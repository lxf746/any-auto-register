"""OpenBlockLabs 浏览器注册流程（Camoufox）。"""
import random, string, time
from typing import Callable, Optional
from urllib.parse import parse_qs, quote, urlparse

from camoufox.sync_api import Camoufox
from core.browser_utils import build_proxy_config, dump_page_debug

AUTH_BASE = "https://auth.openblocklabs.com"
DASHBOARD = "https://dashboard.openblocklabs.com"
CLIENT_ID = "client_01K8YDZSSKDMK8GYTEHBAW4N4S"


def _generate_password() -> str:
    return (
        ''.join(random.choices(string.ascii_uppercase, k=2))
        + ''.join(random.choices(string.digits, k=3))
        + ''.join(random.choices(string.ascii_lowercase, k=5))
        + '!'
    )
def _wait_for_url(page, substring: str, timeout: int = 60) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if substring in page.url:
            return True
        time.sleep(1)
    return False


def _get_wos_session(page, timeout: int = 60) -> str:
    deadline = time.time() + timeout
    while time.time() < deadline:
        for cookie in page.context.cookies():
            if cookie["name"] == "wos-session":
                return cookie["value"]
        time.sleep(1)
    return ""


def _is_cf_full_block(page) -> bool:
    try:
        content = page.content().lower()
        signals = [
            "just a moment",
            "checking your browser",
            "verifying you are human",
            "verify you are human",
            "performing security verification",
            "security check to access",
            "ray id",
        ]
        if any(token in content for token in signals):
            has_form = bool(page.query_selector('input[name="email"], input[type="email"], input[type="password"]'))
            if not has_form:
                return True
    except Exception:
        pass
    return False


def _has_turnstile_iframe(page) -> bool:
    try:
        for frame in page.frames:
            if "challenges.cloudflare.com" in frame.url:
                return True
        return bool(page.evaluate(
            """() => Array.from(document.querySelectorAll('iframe')).some(iframe => (iframe.src || '').includes('challenges.cloudflare.com'))"""
        ))
    except Exception:
        return False


def _is_turnstile_modal_visible(page) -> bool:
    try:
        content = page.content().lower()
        signals = [
            "confirm you are human",
            "verify you are human",
            "verifying you are human",
            "performing security verification",
        ]
        if any(token in content for token in signals):
            return True
        return _has_turnstile_iframe(page)
    except Exception:
        return False


def _click_turnstile_in_iframe(page, log_fn=print) -> bool:
    deadline = time.time() + 15
    cf_frame = None
    while time.time() < deadline:
        for frame in page.frames:
            if "challenges.cloudflare.com" in frame.url:
                cf_frame = frame
                break
        if cf_frame:
            break
        time.sleep(0.5)

    if not cf_frame:
        log_fn("未找到 Cloudflare iframe frame，跳过直接点击")
        return False

    iframe_el = None
    for el in page.query_selector_all("iframe"):
        try:
            src = el.get_attribute("src") or ""
            if "cloudflare.com" in src:
                iframe_el = el
                break
        except Exception:
            continue

    if not iframe_el:
        try:
            iframe_el = cf_frame.frame_element()
        except Exception:
            pass

    if iframe_el:
        try:
            box = None
            for _ in range(10):
                maybe_box = iframe_el.bounding_box()
                if maybe_box and maybe_box["height"] > 10 and maybe_box["y"] >= 0:
                    box = maybe_box
                    break
                time.sleep(0.5)
            if box:
                cx = box["x"] + 24
                cy = box["y"] + box["height"] / 2
                page.mouse.move(cx + random.randint(-5, 5), cy + random.randint(-3, 3))
                time.sleep(random.uniform(0.1, 0.25))
                page.mouse.down()
                time.sleep(random.uniform(0.08, 0.15))
                page.mouse.up()
                log_fn(f"✅ 点击 Turnstile checkbox 坐标: ({cx:.0f}, {cy:.0f})")
                time.sleep(1.5)
                if _is_turnstile_modal_visible(page):
                    page.mouse.move(cx + 12, cy)
                    time.sleep(0.1)
                    page.mouse.down()
                    time.sleep(0.1)
                    page.mouse.up()
                    time.sleep(1)
                return True
        except Exception as exc:
            log_fn(f"Turnstile 坐标点击失败: {exc}")

    try:
        cf_frame.locator("body").click(position={"x": 24, "y": 32}, timeout=5000)
        log_fn("✅ frame 内坐标点击成功")
        return True
    except Exception as exc:
        log_fn(f"frame 内点击失败: {exc}")

    return False


def _wait_cf_full_block_clear(page, timeout: int = 120, log_fn=print) -> None:
    deadline = time.time() + timeout
    warned = False
    clicked = False
    while time.time() < deadline:
        if not _is_cf_full_block(page):
            return
        if not warned:
            log_fn("检测到 Cloudflare 全页拦截，尝试点击验证 checkbox...")
            warned = True
        try:
            viewport = page.viewport_size or {"width": 1280, "height": 720}
            for _ in range(3):
                page.mouse.move(
                    random.randint(100, viewport["width"] - 100),
                    random.randint(100, viewport["height"] - 100),
                )
                time.sleep(random.uniform(0.1, 0.3))
        except Exception:
            pass
        if not clicked:
            clicked = _click_turnstile_in_iframe(page, log_fn)
            if not clicked:
                time.sleep(1)
        else:
            time.sleep(2)
    raise RuntimeError(f"Cloudflare 全页验证未通过: {page.url}")


def _click_continue(page) -> bool:
    for sel in [
        'button[type="submit"]:not([aria-hidden="true"])',
        'button:has-text("Continue")',
        'button:has-text("Sign up")',
        'button:has-text("Next")',
        'button[type="submit"]',
        'button',
    ]:
        try:
            for el in page.query_selector_all(sel):
                if el.is_visible() and el.is_enabled():
                    el.click(timeout=3000)
                    return True
        except Exception:
            continue
    return False


def _handle_turnstile(page, log_fn=print, wait_secs: int = 12) -> bool:
    otp_ready_sel = 'input[autocomplete="one-time-code"], input[data-test="otp-input"], input[data-index="0"]'
    deadline = time.time() + wait_secs
    has_turnstile = False
    while time.time() < deadline:
        if _is_turnstile_modal_visible(page):
            has_turnstile = True
            break
        if page.query_selector(otp_ready_sel):
            return False
        time.sleep(1)

    if not has_turnstile:
        return False

    log_fn("检测到 Turnstile，尝试直接点击 iframe checkbox...")
    solved = _click_turnstile_in_iframe(page, log_fn)
    if not solved:
        log_fn("⚠️ 自动点击失败，等待手动通过（最多90秒）...")
        manual_deadline = time.time() + 90
        while time.time() < manual_deadline:
            if not _is_turnstile_modal_visible(page):
                break
            if page.query_selector(otp_ready_sel):
                break
            time.sleep(2)
    else:
        time.sleep(3)
        if _is_turnstile_modal_visible(page):
            log_fn("Turnstile 仍在显示，等待自动通过...")
            time.sleep(5)
        if not page.query_selector(otp_ready_sel):
            _click_continue(page)
            time.sleep(2)
    return True


def _find_visible_element(page, selectors: list[str], *, require_enabled: bool = False):
    for sel in selectors:
        try:
            for el in page.query_selector_all(sel):
                try:
                    if not el.is_visible():
                        continue
                    if require_enabled and not el.is_enabled():
                        continue
                    return el, sel
                except Exception:
                    continue
        except Exception:
            continue
    return None, ""


def _wait_for_visible_element(page, selectors: list[str], timeout: int = 15, *, require_enabled: bool = False):
    deadline = time.time() + timeout
    while time.time() < deadline:
        el, used_sel = _find_visible_element(page, selectors, require_enabled=require_enabled)
        if el:
            return el, used_sel
        time.sleep(0.2)
    raise RuntimeError(f"未找到可见元素: {' | '.join(selectors)}")


def _read_input_value(input_el) -> str:
    try:
        return input_el.input_value()
    except Exception:
        try:
            return input_el.evaluate("(el) => el.value || ''")
        except Exception:
            return ""


def _fill_visible_input(page, selectors: list[str], value: str, label: str, timeout: int = 15) -> str:
    input_el, used_sel = _wait_for_visible_element(page, selectors, timeout=timeout)
    try:
        input_el.scroll_into_view_if_needed(timeout=2000)
    except Exception:
        pass

    last_error = None
    for _ in range(3):
        try:
            input_el.click(timeout=3000)
        except Exception:
            pass
        try:
            input_el.fill("")
        except Exception:
            pass
        try:
            input_el.type(value, delay=80)
        except Exception as exc:
            last_error = exc

        if _read_input_value(input_el) == value:
            return used_sel

        try:
            input_el.evaluate(
                """(el, nextValue) => {
                    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set;
                    if (setter) setter.call(el, nextValue);
                    else el.value = nextValue;
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    el.dispatchEvent(new Event('blur', { bubbles: true }));
                    return el.value || '';
                }""",
                value,
            )
        except Exception as exc:
            last_error = exc

        if _read_input_value(input_el) == value:
            return used_sel

        time.sleep(0.4)

    current = _read_input_value(input_el)
    raise RuntimeError(f"{label}输入失败: current={current!r}, expected_len={len(value)}, err={last_error}")


def _click_visible_button(page, selectors: list[str], timeout: int = 15) -> str:
    button_el, used_sel = _wait_for_visible_element(page, selectors, timeout=timeout, require_enabled=True)
    try:
        button_el.scroll_into_view_if_needed(timeout=2000)
    except Exception:
        pass

    last_error = None
    for _ in range(2):
        try:
            button_el.click(timeout=3000)
            return used_sel
        except Exception as exc:
            last_error = exc
        try:
            button_el.evaluate("(el) => el.click()")
            return used_sel
        except Exception as exc:
            last_error = exc
        time.sleep(0.2)

    raise RuntimeError(f"点击按钮失败: {last_error}")


def _is_email_verification_ready(page) -> bool:
    otp_selectors = [
        'input[autocomplete="one-time-code"]',
        'input[data-test="otp-input"]',
        'input[data-index="0"]',
    ]
    if "email-verification" in page.url:
        return True
    otp_el, _ = _find_visible_element(page, otp_selectors)
    return bool(otp_el)


def _wait_for_email_verification(page, timeout: int = 20) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _is_email_verification_ready(page):
            return True
        time.sleep(0.2)
    return False


def _advance_to_email_verification(page, btn_selectors: list[str], log_fn=print, timeout: int = 40) -> None:
    deadline = time.time() + timeout
    last_click_at = 0.0
    while time.time() < deadline:
        if _is_email_verification_ready(page):
            return

        if _is_cf_full_block(page):
            _wait_cf_full_block_clear(page, timeout=max(5, int(deadline - time.time())), log_fn=log_fn)
            continue

        _handle_turnstile(page, log_fn, wait_secs=2)
        if _is_email_verification_ready(page):
            return

        try:
            body_text = (page.locator("body").inner_text() or "").strip().lower()
            if "the requested resource was not found" in body_text or body_text == "not found":
                raise RuntimeError(f"中间页返回 Not Found: {page.url}")
        except RuntimeError:
            raise
        except Exception:
            pass

        now = time.time()
        if now - last_click_at >= 1.5:
            btn_el, used_sel = _find_visible_element(page, btn_selectors, require_enabled=True)
            if btn_el:
                try:
                    btn_el.scroll_into_view_if_needed(timeout=2000)
                except Exception:
                    pass
                try:
                    btn_el.click(timeout=3000)
                    log_fn(f"检测到中间页，继续点击按钮: {used_sel}")
                    last_click_at = now
                    time.sleep(2)
                    continue
                except Exception:
                    pass

        time.sleep(0.5)

    raise RuntimeError(f"未进入验证码页面: {page.url}")


def _extract_authorization_session_id(url: str) -> str:
    try:
        parsed = urlparse(url)
        return (parse_qs(parsed.query).get("authorization_session_id") or [""])[0]
    except Exception:
        return ""


def _wait_for_signup_session(page, timeout: int = 30) -> str:
    deadline = time.time() + timeout
    while time.time() < deadline:
        session_id = _extract_authorization_session_id(page.url)
        if session_id:
            return session_id
        try:
            hidden = page.query_selector('input[name="authorization_session_id"][value]')
            if hidden and (hidden.get_attribute("value") or "").strip():
                return hidden.get_attribute("value") or ""
        except Exception:
            pass
        try:
            body_text = (page.locator("body").inner_text() or "").strip().lower()
            if "the requested resource was not found" in body_text or body_text == "not found":
                raise RuntimeError(f"WorkOS 会话初始化失败，页面返回 Not Found: {page.url}")
        except RuntimeError:
            raise
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError(f"等待 authorization_session_id 超时: {page.url}")


class OpenBlockLabsBrowserRegister:
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
        if not password:
            password = _generate_password()
            self.log("未提供密码，已自动生成随机密码")
        self.log(f"注册凭据: {email} / {password}")

        proxy = _build_proxy_config(self.proxy)
        launch_opts = {"headless": self.headless}
        if proxy:
            launch_opts["proxy"] = proxy

        first_name = ''.join(random.choices(string.ascii_lowercase, k=5)).capitalize()
        last_name = ''.join(random.choices(string.ascii_lowercase, k=5)).capitalize()

        with Camoufox(**launch_opts) as browser:
            page = browser.new_page()
            page.add_init_script("""
(function() {
    var screenX = Math.floor(Math.random() * (1200 - 800 + 1)) + 800;
    var screenY = Math.floor(Math.random() * (600 - 400 + 1)) + 400;
    Object.defineProperty(MouseEvent.prototype, 'screenX', {
        get: function() { return this.clientX + screenX; },
        configurable: true
    });
    Object.defineProperty(MouseEvent.prototype, 'screenY', {
        get: function() { return this.clientY + screenY; },
        configurable: true
    });
    Object.defineProperty(PointerEvent.prototype, 'screenX', {
        get: function() { return this.clientX + screenX; },
        configurable: true
    });
    Object.defineProperty(PointerEvent.prototype, 'screenY', {
        get: function() { return this.clientY + screenY; },
        configurable: true
    });
})();
""")
            self.log("打开 OpenBlockLabs 注册页")
            last_open_error = None
            redirect_uri = quote(f"{DASHBOARD}/auth/callback", safe="")
            entry_url = f"{AUTH_BASE}/?client_id={CLIENT_ID}&redirect_uri={redirect_uri}"
            session_id = ""
            for attempt in range(2):
                page.goto(entry_url, wait_until="domcontentloaded", timeout=30000)
                _wait_cf_full_block_clear(page, log_fn=self.log)
                try:
                    page.wait_for_load_state("domcontentloaded", timeout=15000)
                except Exception:
                    pass
                time.sleep(2)
                try:
                    session_id = _wait_for_signup_session(page, timeout=25)
                    signup_url = f"{AUTH_BASE}/sign-up?redirect_uri={redirect_uri}&authorization_session_id={session_id}"
                    if page.url != signup_url:
                        page.goto(signup_url, wait_until="domcontentloaded", timeout=30000)
                        _wait_cf_full_block_clear(page, log_fn=self.log)
                        try:
                            page.wait_for_load_state("domcontentloaded", timeout=15000)
                        except Exception:
                            pass
                        time.sleep(2)
                    break
                except Exception as exc:
                    last_open_error = exc
                    self.log(f"注册会话未就绪，重试打开页面 ({attempt + 1}/2): {exc}")
                    if attempt == 1:
                        raise
                    time.sleep(2)
            if not session_id:
                raise RuntimeError(str(last_open_error or "未获取到 authorization_session_id"))

            for sel, val in [
                ('input[name="first_name"], input[placeholder*="First"]', first_name),
                ('input[name="last_name"], input[placeholder*="Last"]', last_name),
            ]:
                if page.query_selector(sel):
                    page.fill(sel, val)

            email_selectors = [
                'input[name="email"]',
                'input[type="email"]',
                'input[autocomplete="email"]',
                'input[placeholder*="email" i]',
            ]
            pwd_selectors = [
                'input[name="password"]',
                'input[type="password"]',
                'input[autocomplete="new-password"]',
                'input[placeholder*="password" i]',
            ]
            btn_selectors = [
                'button[type="submit"]',
                'button:has-text("Continue")',
                'button:has-text("Sign up")',
            ]

            used_email_sel = _fill_visible_input(page, email_selectors, email, "邮箱", timeout=60)
            self.log(f"已填写邮箱: {used_email_sel}")

            pwd_el, _ = _find_visible_element(page, pwd_selectors)
            if pwd_el:
                used_pwd_sel = _fill_visible_input(page, pwd_selectors, password, "密码", timeout=20)
                self.log(f"已填写密码: {used_pwd_sel}")
                used_btn_sel = _click_visible_button(page, btn_selectors)
                self.log(f"已点击提交按钮: {used_btn_sel}")
                _advance_to_email_verification(page, btn_selectors, log_fn=self.log, timeout=40)
            else:
                used_btn_sel = _click_visible_button(page, btn_selectors)
                self.log(f"已点击继续按钮: {used_btn_sel}")
                _wait_cf_full_block_clear(page, timeout=30, log_fn=self.log)
                _handle_turnstile(page, self.log, wait_secs=15)
                try:
                    page.wait_for_url("**/sign-up/password**", timeout=20000)
                except Exception:
                    pass
                used_pwd_sel = _fill_visible_input(page, pwd_selectors, password, "密码", timeout=20)
                self.log(f"已填写密码: {used_pwd_sel}")
                used_btn_sel = _click_visible_button(page, btn_selectors)
                self.log(f"已点击密码页提交按钮: {used_btn_sel}")
                _advance_to_email_verification(page, btn_selectors, log_fn=self.log, timeout=40)

            time.sleep(2)

            if not _wait_for_email_verification(page, timeout=5):
                debug_paths = dump_page_debug(page, "openblocks_password_fail")
                self.log(
                    f"未进入验证码页面，已保存调试文件到 {debug_paths['screenshot']} 和 {debug_paths['html']}"
                )
                raise RuntimeError(f"未进入验证码页面: {page.url}")

            if not self.otp_callback:
                raise RuntimeError("OpenBlockLabs 注册需要邮箱验证码但未提供 otp_callback")
            self.log("等待 OpenBlockLabs 验证码")
            code = self.otp_callback()
            if not code:
                raise RuntimeError("未获取到验证码")
            code = code.replace("-", "")

            try:
                visible_inputs = page.query_selector_all('input[autocomplete="one-time-code"], input:not([type="hidden"])')
                for input_el in visible_inputs:
                    if input_el.is_visible() and input_el.get_attribute("type") != "email" and input_el.get_attribute("type") != "password":
                        input_el.click()
                        break
                page.keyboard.type(code)
            except Exception as exc:
                self.log(f"填写验证码失败: {exc}")

            _click_continue(page)
            time.sleep(5)

            if not _wait_for_url(page, "dashboard.openblocklabs.com", timeout=60):
                debug_paths = dump_page_debug(page, "openblocks_fail")
                self.log(
                    f"未跳转到 dashboard，已保存调试文件到 {debug_paths['screenshot']} 和 {debug_paths['html']}"
                )
                raise RuntimeError(f"OpenBlockLabs 注册后未跳转到 dashboard: {page.url}")

            wos = _get_wos_session(page, timeout=15)
            if not wos:
                debug_paths = dump_page_debug(page, "openblocks_fail")
                self.log(
                    f"未获取到 wos_session，已保存调试文件到 {debug_paths['screenshot']} 和 {debug_paths['html']}"
                )
                raise RuntimeError("未获取到 wos-session cookie")
            self.log(f"注册成功: {email}")
            return {"email": email, "password": password, "wos_session": wos}
