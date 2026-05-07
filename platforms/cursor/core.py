"""Cursor 注册协议核心实现（WorkOS 新链路）"""
import re, uuid, json, urllib.parse, random, string, time, base64
from typing import Optional, Callable

AUTH   = "https://authenticator.cursor.sh"
CURSOR = "https://cursor.com"
CLIENT_ID = "client_01GS6W3C96KW4WRS6Z93JCE2RJ"
NEXT_ACTION_PASSWORD_GET = "b263a6ee1ac854642026b529d988f13fc058958b"
NEXT_ACTION_PASSWORD_POST = "dfb850e9eeb3eec78d4d33f26012b0f051bb3d74"

# next-router-state-tree（密码步骤：sign-up -> password -> __PAGE__）
NEXT_ROUTER_STATE_TREE_PASSWORD = "%5B%22%22%2C%7B%22children%22%3A%5B%22(main)%22%2C%7B%22children%22%3A%5B%22(root)%22%2C%7B%22children%22%3A%5B%22sign-up%22%2C%7B%22children%22%3A%5B%22password%22%2C%7B%22children%22%3A%5B%22__PAGE__%22%2C%7B%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%2Ctrue%5D%7D"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/145.0.0.0 Safari/537.36")

TURNSTILE_SITEKEY = "0x4AAAAAAAMNIvC45A4Wjjln"
NEXT_ACTION_RADAR_SEND = "a26cb1c7b9ef800ba3a8e9fc9b3153716b5465d4"
NEXT_ACTION_RADAR_VERIFY = "9b09c6bfa44a857e556ba03c3762128e6e5c02e3"
NEXT_ROUTER_STATE_TREE_RADAR_SEND = "%5B%22%22%2C%7B%22children%22%3A%5B%22(main)%22%2C%7B%22children%22%3A%5B%22(root)%22%2C%7B%22children%22%3A%5B%22(fixed-layout)%22%2C%7B%22children%22%3A%5B%22radar-challenge%22%2C%7B%22children%22%3A%5B%22send%22%2C%7B%22children%22%3A%5B%22__PAGE__%22%2C%7B%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%2Ctrue%5D"
NEXT_ROUTER_STATE_TREE_RADAR_VERIFY = "%5B%22%22%2C%7B%22children%22%3A%5B%22(main)%22%2C%7B%22children%22%3A%5B%22(root)%22%2C%7B%22children%22%3A%5B%22(fixed-layout)%22%2C%7B%22children%22%3A%5B%22radar-challenge%22%2C%7B%22children%22%3A%5B%22verify%22%2C%7B%22children%22%3A%5B%22__PAGE__%22%2C%7B%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%2Ctrue%5D"


def _rand_password(n=16):
    chars = string.ascii_letters + string.digits + "!@#$"
    return "".join(random.choices(chars, k=n))


def _boundary():
    return "----WebKitFormBoundary" + "".join(
        random.choices(string.ascii_letters + string.digits, k=16))


def _multipart(fields: list[tuple[str, str]], boundary: str) -> bytes:
    parts = []
    for name, value in fields:
        parts.append(
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
            f"{value}\r\n"
        )
    parts.append(f"--{boundary}--\r\n")
    return "".join(parts).encode()


def _make_signals() -> str:
    data = {
        "createdAtMs": int(time.time() * 1000),
        "timezone": "Asia/Shanghai",
        "language": "zh-CN",
        "hardwareConcurrency": 8,
        "webdriver": False,
        "userAgent": UA,
        "platform": "Win32",
        "screen": {
            "width": 1920, "height": 1080,
            "availWidth": 1920, "availHeight": 1032,
            "windowOuterWidth": 1914, "windowOuterHeight": 1026,
            "colorDepth": 24, "pixelDepth": 24,
        },
        "maxTouchPoints": 0,
        "deviceMemory": 8,
        "devicePixelRatio": 1,
        "pluginsLength": 5,
        "mimeTypesCount": 2,
        "playwrightDetected": False,
        "phantomDetected": False,
        "nightmareDetected": False,
        "seleniumDetected": False,
        "puppeteerDetected": False,
        "submittedAtMs": int(time.time() * 1000) + 1500,
    }
    return base64.b64encode(json.dumps(data).encode()).decode()


class CursorRegister:
    def __init__(self, proxy: str = None, log_fn: Callable = print):
        from curl_cffi import requests as curl_req
        self.log = log_fn
        self.s = curl_req.Session(impersonate="safari17_0")
        if proxy:
            self.s.proxies = {"http": proxy, "https": proxy}
        self.authorization_session_id = ""
        self.redirect_uri = f"{CURSOR}/api/auth/callback"
        self.state_raw = ""
        self.state_encoded = ""
        self._next_action = ""
        self._pending_auth_token = ""
        self._user_id = ""
        self._phone_number = ""
        self._phone_verification_id = ""

    def _extract_action_id(self, text: str) -> str:
        # WorkOS/RSC 响应里 action 节点通常是一个固定长度的 hex id
        m = re.search(r'\\?"id\\?":\\?"([a-fA-F0-9]{40})\\?"', str(text or ""))
        if m:
            return m.group(1)
        # 兜底：兼容 next-action/nextAction 字段附近直接跟 id 的情况
        m2 = re.search(r'next[-_ ]?action[^a-fA-F0-9]{0,50}([a-fA-F0-9]{40})', str(text or ""), flags=re.IGNORECASE)
        return m.group(1) if m else ""

    def _extract_session_id(self, response) -> str:
        try:
            final_url = str(response.url)
            parsed = urllib.parse.urlparse(final_url)
            got = (urllib.parse.parse_qs(parsed.query).get("authorization_session_id") or [""])[0]
            if got:
                return got
            for rr in getattr(response, "history", []) or []:
                loc = rr.headers.get("location", "")
                m = re.search(r"authorization_session_id=([^&]+)", loc)
                if m:
                    return m.group(1)
            # 兜底：从 __Host-state-{session_id} cookie 名中提取
            for c in self.s.cookies.jar:
                name = str(getattr(c, "name", "") or "")
                if name.startswith("__Host-state-") and len(name) > len("__Host-state-"):
                    return name[len("__Host-state-"):]
            # 兜底：从响应文本中提取（部分实现把 session id 放在 RSC/HTML body）
            txt = ""
            try:
                txt = response.text or ""
            except Exception:
                txt = ""
            m = re.search(r"authorization_session_id\"?\s*[:=]\s*\"?([a-zA-Z0-9_-]{8,})\"?", txt)
            if m:
                return m.group(1)
            m2 = re.search(r"authorization_session_id=([a-zA-Z0-9_-]{8,})", txt)
            if m2:
                return m2.group(1)
        except Exception:
            pass
        return ""

    def _base_headers(self, next_action: str, referer: str, boundary: str = None):
        ct = f"multipart/form-data; boundary={boundary}" if boundary else "application/x-www-form-urlencoded"
        return {
            "user-agent": UA,
            "accept": "text/x-component",
            "content-type": ct,
            "origin": AUTH,
            "referer": referer,
            "next-action": next_action,
            "next-router-state-tree": "%5B%22%22%2C%7B%22children%22%3A%5B%22(main)%22%2C%7B%22children%22%3A%5B%22(root)%22%2C%7B%22children%22%3A%5B%22sign-up%22%2C%7B%22children%22%3A%5B%22__PAGE__%22%2C%7B%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%2Ctrue%5D",
        }

    def step1_get_session(self):
        nonce = str(uuid.uuid4())
        state = {"returnTo": "/dashboard", "nonce": nonce}
        # state 分两份：
        # - state_raw：表单字段 1_state 使用（单编码）
        # - state_encoded：URL query state 使用（双编码，和你抓包里的 %257B 对齐）
        self.state_raw = urllib.parse.quote(json.dumps(state, separators=(",", ":")), safe="")
        self.state_encoded = urllib.parse.quote(self.state_raw, safe="")

        # 先请求根态，确保 state 相关 cookie/会话被写入
        init_url = f"{AUTH}/?state={self.state_encoded}"
        try:
            self.s.get(init_url, headers={"user-agent": UA, "accept": "text/html"}, allow_redirects=True)
        except Exception:
            pass

        signup_url = (
            f"{AUTH}/sign-up"
            f"?client_id={CLIENT_ID}"
            f"&state={self.state_encoded}"
            f"&redirect_uri={urllib.parse.quote(self.redirect_uri, safe='')}"
        )

        r = self.s.get(
            signup_url,
            headers={"user-agent": UA, "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"},
            allow_redirects=True,
        )
        self.authorization_session_id = self._extract_session_id(r)
        self._next_action = self._extract_action_id(getattr(r, "text", "") or "")

        if not self.authorization_session_id:
            cookie_names = [str(getattr(c, "name", "") or "") for c in getattr(self.s.cookies, "jar", []) or []]
            focus_names = [n for n in cookie_names if ("state" in n) or ("authorization" in n)]
            self.log(f"[Cursor][DEBUG] step1 url={signup_url}")
            self.log(f"[Cursor][DEBUG] step1 final_url={getattr(r, 'url', '')}")
            self.log(f"[Cursor][DEBUG] step1 state_cookie_like={focus_names[:20]}")
            self.log(f"[Cursor][DEBUG] step1 next_action={self._next_action[:16] if self._next_action else ''}")
        state_cookie_name = None
        for cookie in self.s.cookies.jar:
            if 'state-' in cookie.name:
                state_cookie_name = cookie.name
                break
        return self.state_encoded, state_cookie_name

    def step2_submit_email(self, email, state_encoded):
        bd = _boundary()
        if not self.authorization_session_id:
            raise RuntimeError("缺少 authorization_session_id")
        referer = (
            f"{AUTH}/sign-up"
            f"?state={self.state_encoded}"
            f"&redirect_uri={urllib.parse.quote(self.redirect_uri, safe='')}"
            f"&authorization_session_id={self.authorization_session_id}"
        )
        fields = [
            ("1_bot_detection_token", ""),
            ("1_browser_supports_passkeys", "true"),
            ("1_signals", _make_signals()),
            ("1_first_name", email.split("@")[0][:8] or "user"),
            ("1_last_name", "auto"),
            ("1_email", email),
            ("1_intent", "sign-up"),
            ("1_redirect_uri", self.redirect_uri),
            ("1_authorization_session_id", self.authorization_session_id),
            ("1_state", self.state_raw),
            ("0", '["$K1"]'),
        ]
        body = _multipart(fields, bd)
        r = self.s.post(
            referer,
            headers=self._base_headers(self._next_action, referer, boundary=bd),
            data=body,
            allow_redirects=False,
        )
        nxt = r.headers.get("location", "")
        if "/sign-up/password" not in nxt and r.status_code not in (200, 303):
            raise RuntimeError(f"提交邮箱失败: HTTP {r.status_code}")

        pwd_url = (
            f"{AUTH}/sign-up/password"
            f"?state={self.state_encoded}"
            f"&redirect_uri={urllib.parse.quote(self.redirect_uri, safe='')}"
            f"&authorization_session_id={self.authorization_session_id}"
        )
        # 对齐抓包：GET /sign-up/password 需要 next-action + text/x-component
        r2 = self.s.get(
            pwd_url,
            headers={
                "user-agent": UA,
                "accept": "text/x-component",
                "origin": AUTH,
                "referer": referer,
                "next-action": NEXT_ACTION_PASSWORD_GET,
                "next-url": "/sign-up/password",
                "rsc": "1",
            },
            allow_redirects=True,
        )
        action = self._extract_action_id(getattr(r2, "text", "") or "")
        if action:
            self._next_action = action
        else:
            # 不影响后续：step3 会直接使用 NEXT_ACTION_PASSWORD_POST
            self._next_action = self._next_action or NEXT_ACTION_PASSWORD_POST
            self.log(f"[Cursor][DEBUG] next-action 提取失败（使用固定 POST next-action） url={pwd_url}")

    def step3_submit_password(self, password, email, state_encoded, captcha_solver=None):
        bd = _boundary()
        if not self.authorization_session_id:
            raise RuntimeError("缺少 authorization_session_id")
        captcha_token = ""
        if captcha_solver:
            try:
                # 这一步需要 Turnstile token，否则 Cursor 不会进入 email-verification
                captcha_token = str(captcha_solver.solve_turnstile(AUTH, TURNSTILE_SITEKEY) or "").strip()
            except Exception:
                captcha_token = ""
        referer = (
            f"{AUTH}/sign-up/password"
            f"?state={self.state_encoded}"
            f"&redirect_uri={urllib.parse.quote(self.redirect_uri, safe='')}"
            f"&authorization_session_id={self.authorization_session_id}"
        )
        fields = [
            ("1_bot_detection_token", captcha_token),
            ("1_browser_supports_passkeys", "true"),
            ("1_signals", _make_signals()),
            ("1_first_name", email.split("@")[0][:8] or "user"),
            ("1_last_name", "auto"),
            ("1_email", email),
            ("1_password", password),
            ("1_intent", "sign-up"),
            ("1_redirect_uri", self.redirect_uri),
            ("1_authorization_session_id", self.authorization_session_id),
            ("1_state", self.state_raw),
            ("0", '["$K1"]'),
        ]
        body = _multipart(fields, bd)
        r = self.s.post(
            referer,
            headers={
                **self._base_headers(NEXT_ACTION_PASSWORD_POST, referer, boundary=bd),
                # 对齐抓包：POST 阶段也依赖 correct next-action
                "next-action": NEXT_ACTION_PASSWORD_POST,
            },
            data=body,
            allow_redirects=False,
        )

        text = getattr(r, "text", "") or ""
        m = re.search(r'"pendingAuthenticationToken"\s*:\s*"([^"]+)"', text)
        if not m:
            # 更宽松兜底：可能存在转义或不同字段名附近
            m = re.search(r"pendingAuthenticationToken[^\\n]{0,200}[\"']([^\"']{6,})[\"']", text)
        self._pending_auth_token = m.group(1) if m else ""
        if not self._pending_auth_token:
            idx = text.find("pendingAuthenticationToken")
            snippet = text[idx:idx + 160] if idx != -1 else ""
            self.log(f"[Cursor][DEBUG] pendingAuthenticationToken 提取失败，snippet={snippet[:160]}")
        ev_url = (
            f"{AUTH}/email-verification"
            f"?state={self.state_encoded}"
            f"&redirect_uri={urllib.parse.quote(self.redirect_uri, safe='')}"
            f"&authorization_session_id={self.authorization_session_id}"
        )
        r2 = self.s.get(ev_url, headers={"user-agent": UA, "accept": "text/html", "referer": referer}, allow_redirects=True)
        action = self._extract_action_id(r2.text)
        if action:
            self._next_action = action

    def step4_submit_otp(self, otp, email, state_encoded):
        bd = _boundary()
        referer = (
            f"{AUTH}/email-verification"
            f"?state={self.state_encoded}"
            f"&redirect_uri={urllib.parse.quote(self.redirect_uri, safe='')}"
            f"&authorization_session_id={self.authorization_session_id}"
        )
        fields = [
            ("1_code", str(otp).strip()),
            ("1_redirect_uri", self.redirect_uri),
            ("1_authorization_session_id", self.authorization_session_id),
            ("1_email", email),
            ("1_state", self.state_raw),
        ]
        if self._pending_auth_token:
            fields.append(("1_pending_authentication_token", self._pending_auth_token))
        fields.append(("0", '["$K1"]'))
        body = _multipart(fields, bd)
        r = self.s.post(
            referer,
            headers=self._base_headers(self._next_action, referer, boundary=bd),
            data=body,
            allow_redirects=False,
        )
        # 优先从 x-action-redirect/location 头里提取 code
        loc = r.headers.get("x-action-redirect", "") or r.headers.get("location", "")
        code = ""
        m = re.search(r"code=([^&]+)", loc)
        if m:
            code = m.group(1)

        # 兜底：部分实现可能把 code 放在响应 body 或其它字段中
        if not code:
            text = getattr(r, "text", "") or ""
            m2 = re.search(r"code=([^&\"'\\s]+)", text)
            if not m2:
                m2 = re.search(r'"code"\\s*:\\s*"([^"]+)"', text)
            if m2:
                code = m2.group(1)

        if not code:
            # 打一点调试，方便线上抓问题
            loc_brief = str(loc)[:200]
            try:
                txt_brief = (getattr(r, "text", "") or "")[:200]
            except Exception:
                txt_brief = ""
            self.log(f"[Cursor][DEBUG] step4 提取 code 失败, location={loc_brief}")
            if txt_brief:
                self.log(f"[Cursor][DEBUG] step4 body snippet={txt_brief}")
        text = getattr(r, "text", "") or ""
        if text:
            um = re.search(r"user_[a-z0-9]{10,}", text, flags=re.IGNORECASE)
            if um:
                self._user_id = um.group(0)
            pm = re.search(r"pendingAuthenticationToken[^\\n]{0,200}[\"']([^\"']{6,})[\"']", text)
            if pm and not self._pending_auth_token:
                self._pending_auth_token = pm.group(1)

        return code

    def _normalize_phone(self, phone_number: str) -> tuple[str, str, str]:
        raw = str(phone_number or "").strip()
        digits = re.sub(r"\D+", "", raw)
        if not digits:
            raise RuntimeError("手机号为空")
        if digits.startswith("86") and len(digits) >= 13:
            national = digits[2:]
            country = "+86"
        elif raw.startswith("+"):
            country_digits = re.match(r"^\+(\d{1,4})", raw)
            if country_digits:
                country = f"+{country_digits.group(1)}"
                national = digits[len(country_digits.group(1)):]
            else:
                country = "+86"
                national = digits
        else:
            country = "+86"
            national = digits
        if not national:
            raise RuntimeError("手机号格式无效")
        e164 = f"{country}{national}"
        local = national
        if country == "+86" and len(national) == 11:
            local = f"({national[:3]}){national[3:7]}-{national[7:]}"
        return country, local, e164

    def step5_send_phone_challenge(self, phone_number: str, state_encoded):
        if not self.authorization_session_id:
            raise RuntimeError("缺少 authorization_session_id")
        if not self._pending_auth_token:
            raise RuntimeError("缺少 pending_authentication_token")
        if not self._user_id:
            self.log("[Cursor][DEBUG] user_id 缺失，继续尝试发送手机挑战（可能失败）")
        country_code, local_number, e164 = self._normalize_phone(phone_number)
        self._phone_number = e164
        bd = _boundary()
        send_url = (
            f"{AUTH}/radar-challenge/send"
            f"?user_id={urllib.parse.quote(self._user_id, safe='')}"
            f"&state={self.state_encoded}"
            f"&redirect_uri={urllib.parse.quote(self.redirect_uri, safe='')}"
            f"&authorization_session_id={self.authorization_session_id}"
        )
        fields = [
            ("1_country_code", country_code),
            ("1_local_number", local_number),
            ("1_phone_number", e164),
            ("1_redirect_uri", self.redirect_uri),
            ("1_authorization_session_id", self.authorization_session_id),
            ("1_state", self.state_raw),
            ("1_user_id", self._user_id),
            ("1_pending_authentication_token", self._pending_auth_token),
            ("0", '["$K1"]'),
        ]
        body = _multipart(fields, bd)
        r = self.s.post(
            send_url,
            headers={
                "user-agent": UA,
                "accept": "text/x-component",
                "content-type": f"multipart/form-data; boundary={bd}",
                "origin": AUTH,
                "referer": send_url,
                "next-action": NEXT_ACTION_RADAR_SEND,
                "next-router-state-tree": NEXT_ROUTER_STATE_TREE_RADAR_SEND,
            },
            data=body,
            allow_redirects=False,
        )
        txt = getattr(r, "text", "") or ""
        vm = re.search(r"vrf_[a-z0-9]+", txt, flags=re.IGNORECASE)
        if vm:
            self._phone_verification_id = vm.group(0)
        if not self._phone_verification_id:
            self.log("[Cursor][DEBUG] step5_send 未提取到 verification_id")

    def step6_verify_phone_challenge(self, sms_code: str, state_encoded) -> str:
        if not self.authorization_session_id:
            raise RuntimeError("缺少 authorization_session_id")
        if not self._pending_auth_token:
            raise RuntimeError("缺少 pending_authentication_token")
        if not self._phone_number:
            raise RuntimeError("缺少 phone_number")
        if not self._phone_verification_id:
            raise RuntimeError("缺少 verification_id")
        bd = _boundary()
        verify_url = (
            f"{AUTH}/radar-challenge/verify"
            f"?authorization_session_id={self.authorization_session_id}"
            f"&redirect_uri={urllib.parse.quote(self.redirect_uri, safe='')}"
            f"&state={self.state_encoded}"
        )
        fields = [
            ("1_code", str(sms_code or "").strip()),
            ("1_redirect_uri", self.redirect_uri),
            ("1_authorization_session_id", self.authorization_session_id),
            ("1_state", self.state_raw),
            ("1_verification_id", self._phone_verification_id),
            ("1_phone_number", self._phone_number),
            ("1_pending_authentication_token", self._pending_auth_token),
            ("0", '["$K1"]'),
        ]
        body = _multipart(fields, bd)
        r = self.s.post(
            verify_url,
            headers={
                "user-agent": UA,
                "accept": "text/x-component",
                "content-type": f"multipart/form-data; boundary={bd}",
                "origin": AUTH,
                "referer": verify_url,
                "next-action": NEXT_ACTION_RADAR_VERIFY,
                "next-router-state-tree": NEXT_ROUTER_STATE_TREE_RADAR_VERIFY,
            },
            data=body,
            allow_redirects=False,
        )
        loc = r.headers.get("x-action-redirect", "") or r.headers.get("location", "")
        m = re.search(r"code=([^&]+)", loc)
        if m:
            return m.group(1)
        txt = getattr(r, "text", "") or ""
        m2 = re.search(r'code=([^&"\'\\s]+)', txt)
        if m2:
            return m2.group(1)
        return ""

    def step7_get_token(self, auth_code, state_encoded):
        def _mask(v: str, *, head: int = 6, tail: int = 4) -> str:
            v = str(v or "")
            if not v:
                return ""
            if len(v) <= head + tail:
                return v
            return f"{v[:head]}...{v[-tail:]}"

        def _extract_from_cookies() -> str:
            # 1) 精确命中（最常见）
            for cookie in self.s.cookies.jar:
                if getattr(cookie, "name", "") == "WorkosCursorSessionToken":
                    return urllib.parse.unquote(getattr(cookie, "value", "") or "")

            # 2) 宽松命中：有时 cookie name 可能带前缀（比如 __Host-...）
            candidates = []
            for cookie in self.s.cookies.jar:
                name = str(getattr(cookie, "name", "") or "")
                if "WorkosCursorSessionToken" in name:
                    candidates.append(cookie)
            if candidates:
                # 取第一个非空值
                for cookie in candidates:
                    val = str(getattr(cookie, "value", "") or "")
                    if val:
                        return urllib.parse.unquote(val)

            # 3) 最后兜底：只要是 WorkOS/cursor/session 相关 cookie，并且值看起来“像 token”（长度足够）
            for cookie in self.s.cookies.jar:
                name = str(getattr(cookie, "name", "") or "").lower()
                val = str(getattr(cookie, "value", "") or "")
                if "workos" in name and "session" in name and val and len(val) >= 16:
                    return urllib.parse.unquote(val)
            return ""

        code_q = urllib.parse.quote(str(auth_code or ""), safe="")
        # state 在前面已经是“URL 里使用的最终形态”（类似 %257B...），这里不要再做额外编码，避免三重编码
        state_q = str(state_encoded or self.state_encoded or "")
        url = f"{CURSOR}/api/auth/callback?code={code_q}&state={state_q}"

        r = self.s.get(
            url,
            headers={
                "user-agent": UA,
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                # 某些链路需要 referer 才会写入 session cookie
                "referer": f"{CURSOR}/dashboard",
            },
            allow_redirects=False,
        )
        token = _extract_from_cookies()
        if token:
            return token

        r2 = self.s.get(
            url,
            headers={"user-agent": UA, "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"},
            allow_redirects=True,
        )
        token = _extract_from_cookies()
        if token:
            return token

        # 兜底调试：列出 cookie 名称（不打印完整 token）
        cookie_names = []
        for cookie in self.s.cookies.jar:
            name = str(getattr(cookie, "name", "") or "")
            if "workos" in name.lower() or "cursor" in name.lower() or "session" in name.lower():
                cookie_names.append(name)
        self.log(f"[Cursor][DEBUG] step5 token cookie not found, url={url}")
        self.log(f"[Cursor][DEBUG] step5 relevant cookie names: {cookie_names[:30]}")

        # 如果响应里有 Set-Cookie，尽量展示摘要（同样不打印完整值）
        try:
            set_cookie = None
            # curl_cffi response headers 可能是普通 dict 或 CIMultiDict
            if hasattr(r2, "headers"):
                set_cookie = r2.headers.get("set-cookie") if isinstance(r2.headers, dict) else None
            if set_cookie:
                self.log(f"[Cursor][DEBUG] step5 response set-cookie(brief): {str(set_cookie)[:200]}")
        except Exception:
            pass

        return ""

    def step5_get_token(self, auth_code, state_encoded):
        # 兼容旧调用路径
        return self.step7_get_token(auth_code, state_encoded)

# CursorBrowserRegister 统一从 browser_register.py 导入，避免代码重复
from platforms.cursor.browser_register import CursorBrowserRegister  # noqa: F401
