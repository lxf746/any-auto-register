"""Grok (x.ai) 浏览器注册流程（Camoufox）。"""
import time
from typing import Callable, Optional

from camoufox.sync_api import Camoufox
from core.browser_utils import build_proxy_config, dump_page_debug

ACCOUNTS_URL = "https://accounts.x.ai"
GROK_APP_URL = "https://grok.com"


def _get_cookies(page, names: list) -> dict:
    return {c["name"]: c["value"] for c in page.context.cookies() if c["name"] in names}


def _wait_for_cookies(page, names: list, timeout: int = 120) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        found = _get_cookies(page, names)
        if all(n in found for n in names):
            return found
        time.sleep(1)
    return _get_cookies(page, names)


class GrokBrowserRegister:
    def __init__(
        self,
        *,
        headless: bool,
        proxy: Optional[str] = None,
        otp_callback: Optional[Callable[[], str]] = None,
        log_fn: Callable[[str], None] = print,
    ):
        self.headless = headless
        self.proxy = proxy
        self.otp_callback = otp_callback
        self.log = log_fn

    def run(self, email: str, password: str) -> dict:
        proxy = _build_proxy_config(self.proxy)
        launch_opts = {"headless": self.headless}
        if proxy:
            launch_opts["proxy"] = proxy

        with Camoufox(**launch_opts) as browser:
            page = browser.new_page()
            self.log("打开 Grok 注册页")
            page.goto(f"{ACCOUNTS_URL}/sign-up", wait_until="networkidle", timeout=30000)
            time.sleep(2)

            # Click "Sign up with email" if it exists
            btn_email_sel = 'button:has-text("Sign up with email")'
            if page.query_selector(btn_email_sel):
                page.click(btn_email_sel)
                time.sleep(2)

            # Step 1: fill email
            email_sel = 'input[type="email"], input[name="email"], input[name="username"]'
            page.wait_for_selector(email_sel, timeout=15000)
            page.fill(email_sel, email)

            btn_sel = 'button[type="submit"], button[data-testid="continue"]'
            if page.query_selector(btn_sel):
                page.click(btn_sel)
            time.sleep(3)

            # OTP sent to email
            try:
                page.wait_for_selector('input[name="code"], input[placeholder*="code"], input[placeholder*="Code"]', timeout=20000)
            except Exception:
                fb = ""
                for sel in ['[role="alert"]', '.error']:
                    el = page.query_selector(sel)
                    if el:
                        fb = el.inner_text()
                        break
                raise RuntimeError(f"未进入验证码页面: {fb or page.url}")

            if not self.otp_callback:
                raise RuntimeError("Grok 注册需要邮箱验证码但未提供 otp_callback")
            self.log("等待 Grok 验证码")
            code = self.otp_callback()
            if not code:
                raise RuntimeError("未获取到验证码")

            code_sel = 'input[name="code"], input[data-input-otp="true"]'
            if not page.query_selector(code_sel):
                code_sel = 'input[placeholder*="code"], input[placeholder*="Code"]'
            
            # The input expects 6 characters without hyphen
            clean_code = code.replace("-", "")
            try:
                page.fill(code_sel, clean_code, force=True)
            except:
                page.locator(code_sel).press_sequentially(clean_code)

            confirm_btn = 'button:has-text("Confirm email")'
            if page.query_selector(confirm_btn):
                page.click(confirm_btn, force=True)
            elif page.query_selector(btn_sel):
                page.click(btn_sel, force=True)
            time.sleep(3)

            # May need name + password
            self.log("等待姓名/密码填写步骤")
            for _ in range(15):
                if page.query_selector('input[name="given_name"], input[placeholder*="First"], input[name="password"], input[type="password"]'):
                    break
                time.sleep(1)
            else:
                debug_paths = dump_page_debug(page, "grok_debug")
                self.log(
                    f"未检测到姓名或密码输入框，已保存调试文件到 {debug_paths['screenshot']} 和 {debug_paths['html']}"
                )

            if page.query_selector('input[name="given_name"], input[name="givenName"], input[placeholder*="First"]'):
                import random, string
                first = ''.join(random.choices(string.ascii_lowercase, k=5)).capitalize()
                last = ''.join(random.choices(string.ascii_lowercase, k=5)).capitalize()
                fname_sel = 'input[name="given_name"], input[name="givenName"], input[placeholder*="First"]'
                if page.query_selector(fname_sel):
                    page.fill(fname_sel, first)
                lname_sel = 'input[name="family_name"], input[name="familyName"], input[placeholder*="Last"]'
                if page.query_selector(lname_sel):
                    page.fill(lname_sel, last)
                # DO NOT CLICK YET if password is also on screen
                if not page.query_selector('input[name="password"], input[type="password"]'):
                    if page.query_selector(btn_sel):
                        page.click(btn_sel)
                    time.sleep(2)

            for _ in range(10):
                if page.query_selector('input[name="password"], input[type="password"]'):
                    break
                time.sleep(1)

            if page.query_selector('input[name="password"], input[type="password"]'):
                page.fill('input[name="password"], input[type="password"]', password)
                
                # Try to click any checkbox (like TOS)
                checkboxes = page.query_selector_all('input[type="checkbox"]')
                for cb in checkboxes:
                    try:
                        cb.click(force=True)
                    except:
                        pass
                
                submit_btn = 'button:has-text("Complete sign up"), button:has-text("Sign up"), button[type="submit"]'
                if page.query_selector(submit_btn):
                    page.click(submit_btn)
                elif page.query_selector(btn_sel):
                    page.click(btn_sel)
                time.sleep(3)

            # Wait for sso cookie
            self.log("等待 Grok sso cookie")
            cookies = _wait_for_cookies(page, ["sso"], timeout=60)
            sso = cookies.get("sso", "")
            if not sso:
                debug_paths = dump_page_debug(page, "grok_fail_final")
                self.log(
                    f"未获取到 sso cookie，已保存调试文件到 {debug_paths['screenshot']} 和 {debug_paths['html']}"
                )
                raise RuntimeError("未获取到 Grok sso cookie")
            sso_rw = _get_cookies(page, ["sso-rw"]).get("sso-rw", "")
            self.log(f"注册成功: {email}")
            return {"email": email, "password": password, "sso": sso, "sso_rw": sso_rw}
