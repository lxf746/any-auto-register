"""ChatGPT 浏览器注册流程（Camoufox）。"""
import time
from typing import Callable, Optional

from camoufox.sync_api import Camoufox
from core.browser_utils import build_proxy_config, dump_page_debug

OPENAI_AUTH = "https://auth.openai.com"
CHATGPT_APP = "https://chatgpt.com"


def _wait_for_url(page, substring: str, timeout: int = 60) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if substring in page.url:
            return True
        time.sleep(1)
    return False


def _wait_for_any_selector(page, selectors: list[str], timeout: int = 30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        for sel in selectors:
            try:
                node = page.query_selector(sel)
            except Exception:
                node = None
            if node:
                return sel
        time.sleep(0.5)
    return None


def _click_first(page, selectors: list[str], *, timeout: int = 10) -> str | None:
    found = _wait_for_any_selector(page, selectors, timeout=timeout)
    if not found:
        return None
    try:
        page.click(found)
        return found
    except Exception:
        return None


def _dump_debug(page, prefix: str) -> None:
    return dump_page_debug(page, prefix)


def _get_cookies(page) -> dict:
    return {c["name"]: c["value"] for c in page.context.cookies()}


def _wait_for_access_token(page, timeout: int = 60) -> str:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = page.evaluate("""
            async () => {
                const r = await fetch('/api/auth/session');
                const j = await r.json();
                return j.accessToken || '';
            }
            """)
            if r:
                return r
        except Exception:
            pass
        time.sleep(2)
    return ""


def _overwrite_focused_value(page, value: str) -> None:
    for shortcut in ("Control+A", "Meta+A"):
        try:
            page.keyboard.press(shortcut)
        except Exception:
            pass
    try:
        page.keyboard.press("Backspace")
    except Exception:
        pass
    page.keyboard.type(value)


def _fill_profile(page, log_fn: Callable[[str], None]) -> None:
    import random
    from datetime import datetime

    FIRST_NAMES = [
        "James", "John", "Robert", "Michael", "William", "David", "Emma", "Olivia", "Ava", "Isabella",
        "Sophia", "Mia", "Charlotte", "Amelia", "Harper", "Evelyn", "Liam", "Noah", "Ethan", "Lucas",
    ]
    name = random.choice(FIRST_NAMES)
    current_year = datetime.now().year
    birth_year = random.randint(current_year - 45, current_year - 20)
    birth_month = random.randint(1, 12)
    birth_day = random.randint(1, 28)
    birthdate = f"{birth_year}-{birth_month:02d}-{birth_day:02d}"
    year, month, day = birthdate.split("-")
    age = current_year - int(year)

    name_sel = 'input[name="name"]'
    if page.query_selector(name_sel):
        page.fill(name_sel, f"{name} User")

    date_filled = False
    for attempt in range(3):
        try:
            year_input = page.query_selector('[data-type="year"][contenteditable="true"]')
            month_input = page.query_selector('[data-type="month"][contenteditable="true"]')
            day_input = page.query_selector('[data-type="day"][contenteditable="true"]')
            if year_input and month_input and day_input:
                year_input.click()
                _overwrite_focused_value(page, year)
                month_input.click()
                _overwrite_focused_value(page, month.zfill(2))
                day_input.click()
                _overwrite_focused_value(page, day.zfill(2))
                date_filled = True
                log_fn(f"filled birthday: {birthdate} (attempt {attempt+1})")
                break
        except Exception as e:
            if attempt < 2:
                log_fn(f"birthday fill attempt {attempt+1} failed: {e}")
                time.sleep(0.5)

    if not date_filled:
        for attempt in range(3):
            try:
                age_input = page.query_selector('[name="age"]')
                if age_input:
                    age_input.fill(str(age))
                    log_fn(f"filled age: {age}")
                    break
            except Exception:
                if attempt < 2:
                    time.sleep(0.5)

    submit_btn = 'button[type="submit"], button:has-text("Finish")'
    if page.query_selector(submit_btn):
        page.click(submit_btn)


class ChatGPTBrowserRegister:
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
        entry_selectors = [
            'a[href*="sign-up"]',
            'a[href*="create-account"]',
            'button:has-text("Sign up")',
            'a:has-text("Sign up")',
            'button:has-text("Sign up for free")',
            'a:has-text("Sign up for free")',
        ]
        email_selectors = [
            'input[name="email"]',
            'input[type="email"]',
            'input[autocomplete="username"]',
            'input#email',
        ]
        continue_selectors = [
            'button[type="submit"]',
            'button:has-text("Continue")',
            'button:has-text("Continue with email")',
            'button:has-text("Next")',
        ]
        password_selectors = [
            'input[name="password"]',
            'input[type="password"]',
            'input[autocomplete="new-password"]',
            'input[autocomplete="current-password"]',
        ]
        otp_selectors = [
            'input[name="code"]',
            'input[autocomplete="one-time-code"]',
            'input[inputmode="numeric"]',
            'input[maxlength="1"]',
            'input[placeholder*="code"]',
            'input[placeholder*="Code"]',
        ]

        proxy = _build_proxy_config(self.proxy)
        launch_opts = {"headless": self.headless}
        if proxy:
            launch_opts["proxy"] = proxy
            launch_opts["geoip"] = True

        with Camoufox(**launch_opts) as browser:
            page = browser.new_page()
            self.log("打开 ChatGPT 注册页")
            page.goto(f"{CHATGPT_APP}/auth/login", wait_until="networkidle", timeout=30000)
            time.sleep(2)
            self.log(f"当前页面: {page.url}")

            # 循环点击登录按钮，直到跳转到 auth.openai.com
            login_entry_selectors = [
                'button[data-testid="login-button"]',
                'a[data-testid="login-button"]',
                'button:has-text("Log in")',
                'a:has-text("Log in")',
            ]
            max_retries = 5
            for i in range(max_retries):
                if "auth.openai.com" in page.url:
                    self.log(f"[{i+1}] ✓ 已跳转到 auth.openai.com: {page.url}")
                    break

                self.log(f"[{i+1}/{max_retries}] 点击登录按钮...")
                login_clicked = _click_first(page, login_entry_selectors, timeout=3)
                if login_clicked:
                    self.log(f"[{i+1}] ✓ 点击成功：{login_clicked}")

                time.sleep(2)
            else:
                self.log(f"达到最大重试次数 {max_retries}，当前 URL: {page.url}")

            # Fill email
            email_sel = _wait_for_any_selector(page, email_selectors, timeout=25)
            if not email_sel:
                debug_paths = _dump_debug(page, "chatgpt_email_fail")
                self.log(
                    f"未找到邮箱输入框，已保存调试文件到 {debug_paths['screenshot']} 和 {debug_paths['html']}"
                )
                raise RuntimeError(f"未找到邮箱输入框: {page.url}")
            self.log(f"已定位邮箱输入框: {email_sel}")
            page.fill(email_sel, email)

            used_continue = _click_first(page, continue_selectors, timeout=5)
            if used_continue:
                self.log(f"已点击邮箱页继续按钮: {used_continue}")
            time.sleep(3)

            # Password step
            pwd_sel = _wait_for_any_selector(page, password_selectors, timeout=20)
            if pwd_sel:
                self.log(f"已定位密码输入框: {pwd_sel}")
                page.fill(pwd_sel, password)
                used_continue = _click_first(page, continue_selectors, timeout=5)
                if used_continue:
                    self.log(f"已点击密码页继续按钮: {used_continue}")
                time.sleep(3)

            # OTP step
            otp_sel = _wait_for_any_selector(page, otp_selectors, timeout=25)
            if not otp_sel:
                debug_paths = _dump_debug(page, "chatgpt_otp_fail")
                self.log(
                    f"未进入验证码页面，已保存调试文件到 {debug_paths['screenshot']} 和 {debug_paths['html']}"
                )
                raise RuntimeError(f"未进入验证码页面: {page.url}")

            if not self.otp_callback:
                raise RuntimeError("ChatGPT 注册需要邮箱验证码但未提供 otp_callback")
            self.log("等待 ChatGPT 验证码")
            code = self.otp_callback()
            if not code:
                raise RuntimeError("未获取到验证码")
            self.log(f"已定位验证码输入框: {otp_sel}")
            if otp_sel == 'input[maxlength="1"]':
                try:
                    page.click(otp_sel)
                except Exception:
                    pass
                for digit in str(code).strip():
                    page.keyboard.press(digit)
                    time.sleep(0.1)
            else:
                page.fill(otp_sel, code)
            used_continue = _click_first(page, continue_selectors, timeout=5)
            if used_continue:
                self.log(f"已点击验证码页继续按钮: {used_continue}")
            time.sleep(5)

            # Check for about-you page
            self.log("等待可能的 Name/Birthday 填写步骤...")
            for _ in range(15):
                if "chatgpt.com" in page.url:
                    break
                if page.query_selector('input[name="name"]'):
                    self.log("检测到关于您页面，填写姓名和生日")
                    _fill_profile(page, self.log)
                    time.sleep(5)
                    break
                time.sleep(1)

            # Wait for chatgpt.com
            try:
                page.wait_for_url("**/chatgpt.com**", timeout=45000)
            except Exception:
                if not _wait_for_url(page, "chatgpt.com", timeout=15):
                    debug_paths = _dump_debug(page, "chatgpt_fail")
                    self.log(
                        f"未跳转到应用，已保存调试文件到 {debug_paths['screenshot']} 和 {debug_paths['html']}"
                    )
                    raise RuntimeError(f"ChatGPT 注册后未跳转到应用: {page.url}")

            time.sleep(3)
            # Find and click Skip if onboarding popup appears
            skip_btn = 'button:has-text("Skip")'
            if page.query_selector(skip_btn):
                self.log("点击 Skip 跳过引导")
                try:
                    page.click(skip_btn, timeout=5000)
                except Exception:
                    pass
            time.sleep(3)

            time.sleep(3)
            access_token = _wait_for_access_token(page, timeout=30)
            cookies_dict = _get_cookies(page)
            cookie_str = "; ".join([f"{k}={v}" for k, v in cookies_dict.items()])
            self.log(f"注册成功: {email}")
            return {
                "email": email, "password": password,
                "access_token": access_token,
                "refresh_token": "", "id_token": "",
                "session_token": cookies_dict.get("__Secure-next-auth.session-token", ""),
                "workspace_id": "", "cookies": cookie_str,
                "profile": {},
            }
