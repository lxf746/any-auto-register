"""Cursor 注册协议核心实现（WorkOS 新链路）"""
import re, uuid, json, urllib.parse, random, string, time, base64, html, os
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
NEXT_ACTION_SIGNIN_ENTRY = "d0b05a2a36fbe69091c2f49016138171d5c1e4cd"
NEXT_ACTION_SIGNIN_PASSWORD_POST = "c2fc11e532fe042139569a5d97c300efa17bc4f4"
NEXT_ROUTER_STATE_TREE_SIGNIN_PASSWORD = "%5B%22%22%2C%7B%22children%22%3A%5B%22(main)%22%2C%7B%22children%22%3A%5B%22(root)%22%2C%7B%22children%22%3A%5B%22(sign-in)%22%2C%7B%22children%22%3A%5B%22password%22%2C%7B%22children%22%3A%5B%22__PAGE__%22%2C%7B%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%2Ctrue%5D"
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
    def __init__(self, proxy: str = None, log_fn: Callable = print, extra: dict | None = None):
        from curl_cffi import requests as curl_req
        self.log = log_fn
        self.s = curl_req.Session(impersonate="safari17_0")
        self._proxy_url = str(proxy or "").strip()
        if self._proxy_url and "://" not in self._proxy_url:
            self._proxy_url = f"http://{self._proxy_url}"
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
        self._browser_ua = ""
        self._cf_prewarmed = False
        self._radar_send_url = ""
        self._radar_send_action = ""
        self._email_for_reauth = ""
        self._password_for_reauth = ""
        self._diag_mode = False
        self._phone_verified = False

        # 可选：注入 Cloudflare clearance cookies，提升 radar-challenge/send 成功率（纯协议场景）
        extra = dict(extra or {})
        self._extra = dict(extra)
        # radar-challenge（发短信/验短信）这两步对出口环境更敏感：
        # 默认不走平台注册代理，除非显式开启 cursor_radar_use_proxy=true
        self._radar_use_proxy = str(extra.get("cursor_radar_use_proxy") or "").strip().lower() in ("1", "true", "yes", "on")
        # 协议优先：禁用浏览器手动采集 cf_clearance，仅走协议 + captcha provider 方案
        self._auto_fetch_cf_clearance = False
        self._cf_fetch_timeout = max(30, int(str(extra.get("cursor_cf_fetch_timeout") or "180").strip() or "180"))
        self._cf_fetch_headless = False
        self._cf_fetch_use_proxy = False
        self._cf_clearance = str(
            extra.get("cursor_cf_clearance")
            or extra.get("cf_clearance")
            or ""
        ).strip()
        self._cf_bm = str(
            extra.get("cursor_cf_bm")
            or extra.get("__cf_bm")
            or ""
        ).strip()
        self._cfuvid = str(
            extra.get("cursor_cfuvid")
            or extra.get("_cfuvid")
            or ""
        ).strip()
        self._diag_mode = str(extra.get("cursor_diag_mode") or "").strip().lower() in ("1", "true", "yes", "on")
        if self._cf_clearance:
            try:
                self.s.cookies.set("cf_clearance", self._cf_clearance, domain="authenticator.cursor.sh", path="/")
            except Exception:
                pass
        if self._cf_bm:
            try:
                self.s.cookies.set("__cf_bm", self._cf_bm, domain="authenticator.cursor.sh", path="/")
            except Exception:
                pass
        if self._cfuvid:
            try:
                self.s.cookies.set("_cfuvid", self._cfuvid, domain="authenticator.cursor.sh", path="/")
            except Exception:
                pass
        if self._cf_clearance or self._cf_bm or self._cfuvid:
            self.log(
                f"[Cursor][DEBUG] 注入 CF cookies: cf_clearance={'Y' if self._cf_clearance else 'N'} "
                f"__cf_bm={'Y' if self._cf_bm else 'N'} _cfuvid={'Y' if self._cfuvid else 'N'}"
            )
        if self._diag_mode:
            self.log("[Cursor][TRACE] 诊断模式已启用")

    def _diag(self, msg: str) -> None:
        if self._diag_mode:
            self.log(f"[Cursor][TRACE] {msg}")

    def _diag_dump_text(self, tag: str, text: str) -> str:
        if (not self._diag_mode) or (not text):
            return ""
        try:
            root = os.path.abspath(os.path.join(os.getcwd(), "runtime_logs", "cursor_diag"))
            os.makedirs(root, exist_ok=True)
            ts = int(time.time() * 1000)
            safe_tag = re.sub(r"[^a-zA-Z0-9._-]+", "_", str(tag or "dump"))
            p = os.path.join(root, f"{safe_tag}_{ts}.txt")
            with open(p, "w", encoding="utf-8") as f:
                f.write(str(text))
            self._diag(f"dump saved: {p}")
            return p
        except Exception as e:
            self._diag(f"dump failed: {e}")
            return ""

    def _current_ua(self) -> str:
        return str(self._browser_ua or UA)

    def _inject_cf_cookies(self, clearance: str = "", bm: str = "", cfuvid: str = "") -> None:
        clearance = str(clearance or "").strip()
        bm = str(bm or "").strip()
        cfuvid = str(cfuvid or "").strip()
        if clearance:
            try:
                self.s.cookies.set("cf_clearance", clearance, domain="authenticator.cursor.sh", path="/")
                self._cf_clearance = clearance
            except Exception:
                pass
        if bm:
            try:
                self.s.cookies.set("__cf_bm", bm, domain="authenticator.cursor.sh", path="/")
                self._cf_bm = bm
            except Exception:
                pass
        if cfuvid:
            try:
                self.s.cookies.set("_cfuvid", cfuvid, domain="authenticator.cursor.sh", path="/")
                self._cfuvid = cfuvid
            except Exception:
                pass

    def _inject_browser_cookies(self, cookies: list[dict]) -> int:
        injected = 0
        for ck in cookies or []:
            if not isinstance(ck, dict):
                continue
            name = str(ck.get("name") or "").strip()
            value = str(ck.get("value") or "")
            domain = str(ck.get("domain") or "").strip() or "authenticator.cursor.sh"
            path = str(ck.get("path") or "/").strip() or "/"
            if not name:
                continue
            # 仅同步 authenticator 相关 cookie，避免污染其它域
            if "authenticator.cursor.sh" not in domain and "cursor.sh" not in domain:
                continue
            try:
                self.s.cookies.set(name, value, domain=domain.lstrip("."), path=path)
                injected += 1
            except Exception:
                continue
        return injected

    def _dedupe_session_cookies(self) -> int:
        """去重同名同域同路径 cookie，减少会话污染。"""
        try:
            jar = getattr(self.s.cookies, "jar", None)
            if jar is None:
                return 0
            seen: set[tuple[str, str, str]] = set()
            remove_keys: list[tuple[str, str, str]] = []
            for c in list(jar):
                name = str(getattr(c, "name", "") or "")
                domain = str(getattr(c, "domain", "") or "")
                path = str(getattr(c, "path", "") or "/")
                key = (name, domain, path)
                if key in seen:
                    remove_keys.append(key)
                else:
                    seen.add(key)
            removed = 0
            for name, domain, path in remove_keys:
                try:
                    jar.clear(domain=domain, path=path, name=name)
                    removed += 1
                except Exception:
                    continue
            return removed
        except Exception:
            return 0

    def _has_cf_clearance_cookie(self) -> bool:
        try:
            names = [str(getattr(c, "name", "") or "") for c in getattr(self.s.cookies, "jar", []) or []]
        except Exception:
            names = []
        return "cf_clearance" in names

    def _try_fetch_cf_clearance_with_browser(self) -> bool:
        if not self._auto_fetch_cf_clearance:
            return False
        self.log("[Cursor][DEBUG] 准备启动浏览器采集 cf_clearance...")
        try:
            from camoufox.sync_api import Camoufox
        except Exception as e:
            self.log(f"[Cursor][DEBUG] 浏览器采集不可用（缺少 camoufox）: {e}")
            return False

        launch_opts = {"headless": bool(self._cf_fetch_headless)}
        try:
            current_proxies = getattr(self.s, "proxies", None) or {}
            proxy_url = str((current_proxies.get("https") or current_proxies.get("http") or "")).strip()
        except Exception:
            proxy_url = ""
        if self._cf_fetch_use_proxy and proxy_url:
            launch_opts["proxy"] = {"server": proxy_url}

        try:
            with Camoufox(**launch_opts) as browser:
                page = browser.new_page()
                try:
                    self._browser_ua = str(page.evaluate("() => navigator.userAgent") or "").strip()
                except Exception:
                    self._browser_ua = ""
                target = (
                    f"{AUTH}/sign-up"
                    f"?client_id={CLIENT_ID}"
                    f"&state={self.state_encoded or ''}"
                    f"&redirect_uri={urllib.parse.quote(self.redirect_uri, safe='')}"
                )
                page.goto(target, wait_until="domcontentloaded", timeout=60000)
                self.log(
                    f"[Cursor][DEBUG] 浏览器已打开验证页，请在 {self._cf_fetch_timeout}s 内完成 Cloudflare 验证..."
                )
                deadline = time.time() + self._cf_fetch_timeout
                while time.time() < deadline:
                    try:
                        ck_list = browser.contexts[0].cookies()
                    except Exception:
                        ck_list = []
                    cf = ""
                    bm = ""
                    for ck in ck_list:
                        name = str((ck or {}).get("name") or "")
                        if name == "cf_clearance":
                            cf = str((ck or {}).get("value") or "")
                        elif name == "__cf_bm":
                            bm = str((ck or {}).get("value") or "")
                    if cf:
                        synced = self._inject_browser_cookies(ck_list)
                        self._inject_cf_cookies(cf, bm)
                        self.log(
                            f"[Cursor][DEBUG] 浏览器采集 cf_clearance 成功，已注入当前会话（同步 cookies={synced}）"
                        )
                        if self._browser_ua:
                            self.log("[Cursor][DEBUG] 已启用浏览器 UA 用于 Radar 请求")
                        return True
                    time.sleep(1)
        except Exception as e:
            self.log(f"[Cursor][DEBUG] 浏览器采集 cf_clearance 失败: {e}")
            return False

        self.log("[Cursor][DEBUG] 浏览器采集 cf_clearance 超时")
        return False

    def _try_fetch_cf_assets_with_captcha5s(self, captcha_solver=None, target_url: str = "") -> bool:
        """使用验证码 provider 的 CloudFlare5s 能力获取 cf cookies（同代理出口）。"""
        solver = captcha_solver
        preferred_solver_key = str((self._extra or {}).get("cursor_cf5s_solver") or "").strip().lower()
        require_proxy = str((self._extra or {}).get("cursor_cf5s_require_proxy") or "1").strip().lower() in ("1", "true", "yes", "on")
        max_rounds = 40
        try:
            max_rounds = max(1, int(str((self._extra or {}).get("cursor_cf5s_max_rounds") or "40").strip() or "40"))
        except Exception:
            max_rounds = 40
        if preferred_solver_key:
            try:
                from core.base_captcha import create_captcha_solver
                solver = create_captcha_solver(preferred_solver_key, self._extra)
            except Exception as e:
                self.log(f"[Cursor][DEBUG] 加载 cursor_cf5s_solver={preferred_solver_key} 失败: {e}")
                return False
        if solver is None or not hasattr(solver, "solve_cloudflare5s"):
            return False
        provider_name = str(getattr(getattr(solver, "__class__", object), "__name__", "CaptchaProvider") or "CaptchaProvider")
        try:
            current_proxies = getattr(self.s, "proxies", None) or {}
            proxy_url = str((current_proxies.get("https") or current_proxies.get("http") or "")).strip()
        except Exception:
            proxy_url = ""
        # radar 阶段默认可能会禁用代理，但 5s 盾必须用“任务原始代理”
        if not proxy_url:
            proxy_url = str(self._proxy_url or "").strip()
        if not proxy_url:
            msg = f"{provider_name} CloudFlare5s 需要代理，但当前任务未配置代理（proxy_pool 为空或任务未指定 proxy）"
            self.log(f"[Cursor][DEBUG] {msg}")
            if require_proxy:
                raise RuntimeError(msg)
            return False
        try:
            self.log(f"[Cursor][DEBUG] {provider_name} CloudFlare5s 开始: url={str((target_url or AUTH))[:120]} proxy=Y")
            started = time.time()
            result = solver.solve_cloudflare5s(
                target_url or AUTH,
                proxy=proxy_url,
                rq_data={"max_rounds": max_rounds},
            )
            self._diag(f"cf5s elapsed_ms={int((time.time() - started) * 1000)}")
        except NotImplementedError:
            return False
        except Exception as e:
            self.log(f"[Cursor][DEBUG] {provider_name} CloudFlare5s 失败: {e}")
            return False

        cookies = dict((result or {}).get("cookies") or {})
        headers = dict((result or {}).get("headers") or {})
        clearance = str(cookies.get("cf_clearance") or "")
        bm = str(cookies.get("__cf_bm") or "")
        cfuvid = str(cookies.get("_cfuvid") or "")
        if not clearance and not bm and not cfuvid:
            self.log(f"[Cursor][DEBUG] {provider_name} CloudFlare5s 未返回可注入 cookie")
            return False

        self._inject_cf_cookies(clearance, bm, cfuvid)
        # CloudFlare5s 结果要求同 IP/UA/TLS 复用；这里同步 UA，并保留代理到 radar 阶段。
        ua = str(headers.get("user-agent") or headers.get("User-Agent") or "").strip()
        if ua:
            self._browser_ua = ua
        self._radar_use_proxy = True
        tls_v = str((result or {}).get("tls_version") or "").strip()
        self.log(
            f"[Cursor][DEBUG] {provider_name} CloudFlare5s 注入成功: "
            f"cf_clearance={'Y' if clearance else 'N'} __cf_bm={'Y' if bm else 'N'} "
            f"_cfuvid={'Y' if cfuvid else 'N'} ua={'Y' if ua else 'N'} tls={tls_v or 'n/a'}"
        )
        return True

    def _post_phone_verify_prewarm(self, *, captcha_solver=None) -> None:
        """手机号验证成功后补一次 CF5s + 预热 authenticator 首页。

        参考抓包：验证完手机号后仍会继续访问 authenticator/WorkOS 链路，
        若缺少 cf_clearance，后续请求容易被 5s 盾拦截。
        """
        enabled_raw = str((self._extra or {}).get("cursor_post_phone_verify_cf5s") or "1").strip().lower()
        if enabled_raw not in ("1", "true", "yes", "on"):
            return

        # 先确保有 cf_clearance（必要时走 CloudFlare5s provider）
        if not self._has_cf_clearance_cookie():
            try:
                self._try_fetch_cf_assets_with_captcha5s(
                    captcha_solver=captcha_solver,
                    target_url=f"{AUTH}/",
                )
            except Exception as e:
                # 这里不强制失败：让后续按原逻辑继续（但大概率会被 CF 拦）
                self.log(f"[Cursor][DEBUG] post-verify CF5s 获取失败: {e}")

        # 再对齐抓包：GET authenticator.cursor.sh/ 预热并落 cookie
        try:
            self.s.get(
                f"{AUTH}/",
                headers={
                    "user-agent": self._current_ua(),
                    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                },
                allow_redirects=True,
            )
        except Exception as e:
            self.log(f"[Cursor][DEBUG] post-verify 预热 AUTH/ 失败: {e}")

        # 带上 client_id/state/session_id 的入口页再预热一次（更贴近实际跳转）
        try:
            if self.authorization_session_id and self.state_encoded:
                warm_url = (
                    f"{AUTH}/?client_id={CLIENT_ID}"
                    f"&redirect_uri={urllib.parse.quote(self.redirect_uri, safe='')}"
                    f"&state={self.state_encoded}"
                    f"&authorization_session_id={self.authorization_session_id}"
                )
                self.s.get(
                    warm_url,
                    headers={
                        "user-agent": self._current_ua(),
                        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    },
                    allow_redirects=True,
                )
        except Exception as e:
            self.log(f"[Cursor][DEBUG] post-verify 预热入口页失败: {e}")

    def _extract_action_id(self, text: str, *, prefer_ids: Optional[list[str]] = None) -> str:
        raw = str(text or "")
        variants = [raw]
        # 增强：对常见编码形态做解码后再匹配（RSC 场景经常多层转义）
        try:
            variants.append(html.unescape(raw))
        except Exception:
            pass
        try:
            variants.append(urllib.parse.unquote(raw))
        except Exception:
            pass
        try:
            variants.append(urllib.parse.unquote(urllib.parse.unquote(raw)))
        except Exception:
            pass
        probe = "\n".join(v for v in variants if v)
        prefer_set = {str(x or "").lower() for x in (prefer_ids or []) if str(x or "").strip()}
        if prefer_set:
            # 先命中偏好 action（用于 radar/send 这种已知 action 的页面）
            for pref in prefer_set:
                if pref and pref in probe.lower():
                    return pref

        # WorkOS/RSC 响应里 action 节点通常是一个固定长度的 hex id
        m = re.search(r'\\?"id\\?":\\?"([a-fA-F0-9]{40})\\?"', probe)
        if m:
            return m.group(1)
        # 兜底：兼容 next-action/nextAction 字段附近直接跟 id 的情况
        m2 = re.search(r'next[-_ ]?action[^a-fA-F0-9]{0,50}([a-fA-F0-9]{40})', probe, flags=re.IGNORECASE)
        if m2:
            return m2.group(1)
        # 再兜底：RSC 文本里直接抓 40 位 hex（避开已知常量）
        cands = re.findall(r"\b([a-fA-F0-9]{40})\b", probe)
        for cand in cands:
            low = cand.lower()
            if low in prefer_set:
                return cand
            if low not in {NEXT_ACTION_PASSWORD_GET, NEXT_ACTION_PASSWORD_POST, NEXT_ACTION_RADAR_SEND, NEXT_ACTION_RADAR_VERIFY}:
                return cand
        return ""

    def _extract_action_id_from_headers(self, headers, *, prefer_ids: Optional[list[str]] = None) -> str:
        if not headers:
            return ""
        try:
            items = list(getattr(headers, "items", lambda: [])())
        except Exception:
            items = []
        if not items and isinstance(headers, dict):
            items = list(headers.items())
        header_blob = "\n".join(f"{k}: {v}" for k, v in items if k is not None)
        return self._extract_action_id(header_blob, prefer_ids=prefer_ids)

    def _extract_verification_id(self, text: str) -> str:
        probe = str(text or "")
        if not probe:
            return ""
        variants = [probe]
        try:
            variants.append(html.unescape(probe))
        except Exception:
            pass
        try:
            variants.append(urllib.parse.unquote(probe))
        except Exception:
            pass
        try:
            variants.append(urllib.parse.unquote(urllib.parse.unquote(probe)))
        except Exception:
            pass
        merged = "\n".join(v for v in variants if v)
        # 1) 常见 ID 形态
        m = re.search(r"\b(vrf_[a-z0-9]+)\b", merged, flags=re.IGNORECASE)
        if m:
            return m.group(1)
        # 2) 键值对形态
        m = re.search(r'verification[_-]?id[^a-zA-Z0-9]{0,10}["\']?([a-zA-Z0-9_-]{12,})["\']?', merged, flags=re.IGNORECASE)
        if m:
            return m.group(1)
        # 3) __PAGE__ query 形态：...__PAGE__?{"...","verification_id":"..."}
        m = re.search(r"__PAGE__\?\{[^}]{0,1200}\}", merged)
        if m:
            blob = m.group(0)
            m2 = re.search(r'"verification[_-]?id"\s*:\s*"([^"]+)"', blob, flags=re.IGNORECASE)
            if m2:
                return m2.group(1)
        return ""

    def _extract_radar_hidden_fields(self, text: str) -> tuple[str, str]:
        """从 radar-challenge/send RSC 文本提取 user_id 与 pending_authentication_token。"""
        probe = str(text or "")
        if not probe:
            return "", ""
        variants = [probe]
        try:
            variants.append(html.unescape(probe))
        except Exception:
            pass
        try:
            variants.append(urllib.parse.unquote(probe))
        except Exception:
            pass
        merged = "\n".join(v for v in variants if v)
        user_id = ""
        pending = ""
        # 优先提 extraHiddenFormFields（最贴近页面真实提交）
        m_user = re.search(r'"user_id"\s*:\s*"([^"]+)"', merged, flags=re.IGNORECASE)
        if m_user:
            user_id = m_user.group(1)
        m_pending = re.search(r'"pending_authentication_token"\s*:\s*"([^"]+)"', merged, flags=re.IGNORECASE)
        if m_pending:
            pending = m_pending.group(1)
        return user_id, pending

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
            "accept-language": "zh-CN,zh;q=0.9",
            "content-type": ct,
            "origin": AUTH,
            "referer": referer,
            "next-action": next_action,
            "next-router-state-tree": "%5B%22%22%2C%7B%22children%22%3A%5B%22(main)%22%2C%7B%22children%22%3A%5B%22(root)%22%2C%7B%22children%22%3A%5B%22sign-up%22%2C%7B%22children%22%3A%5B%22__PAGE__%22%2C%7B%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%2Ctrue%5D",
        }

    def _radar_common_headers(self, *, referer: str, boundary: str, next_action: str, state_tree: str) -> dict:
        trace_id = uuid.uuid4().hex
        span_id = trace_id[:16]
        next_url = "/radar-challenge/send"
        try:
            u = urllib.parse.urlparse(str(referer or ""))
            if u.path:
                next_url = u.path
                if u.query:
                    next_url = f"{next_url}?{u.query}"
        except Exception:
            pass
        headers = {
            "user-agent": self._current_ua(),
            "accept": "text/x-component",
            "accept-language": "zh-CN,zh;q=0.9",
            "content-type": f"multipart/form-data; boundary={boundary}",
            "origin": AUTH,
            "referer": referer,
            "next-action": next_action,
            "next-router-state-tree": state_tree,
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "priority": "u=1, i",
            "rsc": "1",
            "next-url": next_url,
            "sentry-trace": f"{trace_id}-{span_id}-0",
            "baggage": "sentry-environment=production,sentry-sampled=false,sentry-sample_rate=0.001",
        }
        ua = self._current_ua()
        if ("Chrome/" in ua) or ("Edg/" in ua):
            edg_m = re.search(r"Edg/(\d+)", ua)
            chr_m = re.search(r"Chrome/(\d+)", ua)
            if edg_m:
                e = edg_m.group(1)
                c = (chr_m.group(1) if chr_m else e)
                headers["sec-ch-ua"] = f'"Microsoft Edge";v="{e}", "Not.A/Brand";v="8", "Chromium";v="{c}"'
            elif chr_m:
                c = chr_m.group(1)
                headers["sec-ch-ua"] = f'"Chromium";v="{c}", "Not.A/Brand";v="8"'
            headers["sec-ch-ua-mobile"] = "?0"
            headers["sec-ch-ua-platform"] = '"Windows"'
        return headers

    def step1_get_session(self):
        def _do_step1_once():
            # 先请求根态，确保 state 相关 cookie/会话被写入
            init_url = f"{AUTH}/?state={self.state_encoded}"
            try:
                self.s.get(init_url, headers={"user-agent": self._current_ua(), "accept": "text/html"}, allow_redirects=True)
            except Exception:
                pass

            signup_url = (
                f"{AUTH}/sign-up"
                f"?client_id={CLIENT_ID}"
                f"&state={self.state_encoded}"
                f"&redirect_uri={urllib.parse.quote(self.redirect_uri, safe='')}"
            )

            r_local = self.s.get(
                signup_url,
                headers={"user-agent": self._current_ua(), "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"},
                allow_redirects=True,
            )
            return signup_url, r_local

        nonce = str(uuid.uuid4())
        state = {"returnTo": "https://cursor.com/dashboard", "nonce": nonce}
        # state 分两份：
        # - state_raw：表单字段 1_state 使用（单编码）
        # - state_encoded：URL query state 使用（双编码，和你抓包里的 %257B 对齐）
        self.state_raw = urllib.parse.quote(json.dumps(state, separators=(",", ":")), safe="")
        self.state_encoded = urllib.parse.quote(self.state_raw, safe="")

        signup_url, r = _do_step1_once()
        self._diag(f"step1 signup_url={signup_url}")
        self.authorization_session_id = self._extract_session_id(r)
        self._next_action = self._extract_action_id(getattr(r, "text", "") or "")

        # 首次未拿到 session_id：协议链路直接重试一次（不走浏览器手动采集）
        if not self.authorization_session_id:
            self.log("[Cursor][DEBUG] step1 未获取到 authorization_session_id，协议重试一次...")
            signup_url, r = _do_step1_once()
            self.authorization_session_id = self._extract_session_id(r)
            self._next_action = self._extract_action_id(getattr(r, "text", "") or "")

        if not self.authorization_session_id:
            cookie_names = [str(getattr(c, "name", "") or "") for c in getattr(self.s.cookies, "jar", []) or []]
            focus_names = [n for n in cookie_names if ("state" in n) or ("authorization" in n)]
            self.log(f"[Cursor][DEBUG] step1 url={signup_url}")
            self.log(f"[Cursor][DEBUG] step1 final_url={getattr(r, 'url', '')}")
            self.log(f"[Cursor][DEBUG] step1 state_cookie_like={focus_names[:20]}")
            self.log(f"[Cursor][DEBUG] step1 next_action={self._next_action[:16] if self._next_action else ''}")
            try:
                body = str(getattr(r, "text", "") or "")
                if body:
                    self.log(f"[Cursor][DEBUG] step1 body snippet={body[:220].replace(chr(10), ' ')}")
            except Exception:
                pass
        state_cookie_name = None
        for cookie in self.s.cookies.jar:
            if 'state-' in cookie.name:
                state_cookie_name = cookie.name
                break
        self._diag(
            f"step1 done status={getattr(r,'status_code','')} final_url={getattr(r,'url','')} "
            f"session_id={(self.authorization_session_id or '')[:8]}..."
        )
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
        self._diag(
            f"step2 post status={getattr(r,'status_code','')} "
            f"location={r.headers.get('location','')[:120]}"
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
        self._email_for_reauth = str(email or "").strip()
        self._password_for_reauth = str(password or "")
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
        self._diag(
            f"step3 post status={getattr(r,'status_code','')} "
            f"xredir={(r.headers.get('x-action-redirect','') or r.headers.get('location',''))[:140]} "
            f"captcha_len={len(captcha_token)}"
        )

        text = getattr(r, "text", "") or ""
        # 调试：记录触发“发邮件验证码”的接口返回内容
        # 重点：看看 Cursor 是否真正进入 email-verification，以及 pendingAuthenticationToken 是否存在。
        try:
            loc = r.headers.get("x-action-redirect", "") or r.headers.get("location", "") or ""
        except Exception:
            loc = ""
        self.log(
            f"[Cursor][DEBUG] step3 触发验证码 POST status={getattr(r, 'status_code', '')} "
            f"captcha_token_len={len(captcha_token)} "
            f"redirect={str(loc)[:120]}"
        )
        if text:
            self.log(f"[Cursor][DEBUG] step3 POST body snippet={text[:220].replace(chr(10), ' ')}")
        m = re.search(r'"pendingAuthenticationToken"\s*:\s*"([^"]+)"', text)
        if not m:
            # 更宽松兜底：可能存在转义或不同字段名附近
            m = re.search(r"pendingAuthenticationToken[^\\n]{0,200}[\"']([^\"']{6,})[\"']", text)
        self._pending_auth_token = m.group(1) if m else ""
        if not self._pending_auth_token:
            idx = text.find("pendingAuthenticationToken")
            snippet = text[idx:idx + 160] if idx != -1 else ""
            self.log(f"[Cursor][DEBUG] pendingAuthenticationToken 提取失败，snippet={snippet[:160]}")
        else:
            self.log(f"[Cursor][DEBUG] pendingAuthenticationToken 提取成功，len={len(self._pending_auth_token)}")
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
        # 调试：看看 email-verification 页面的响应是否正常
        self.log(f"[Cursor][DEBUG] step3 GET /email-verification status={getattr(r2, 'status_code', '')} next_action={action or ''}")
        if not action and getattr(r2, "text", ""):
            self.log(f"[Cursor][DEBUG] step3 email-verification body snippet={r2.text[:220].replace(chr(10), ' ')}")

    def refresh_phone_context_via_signin_password(self, *, captcha_solver=None) -> bool:
        """按登录链路（邮箱+密码）刷新 phone challenge 上下文。"""
        email = str(self._email_for_reauth or "").strip()
        password = str(self._password_for_reauth or "")
        if not email or not password:
            self.log("[Cursor][DEBUG] signin 刷新上下文跳过：缺少 email/password")
            return False
        if not self.authorization_session_id:
            self.log("[Cursor][DEBUG] signin 刷新上下文跳过：缺少 authorization_session_id")
            return False

        signin_url = (
            f"{AUTH}/?client_id={CLIENT_ID}"
            f"&redirect_uri={urllib.parse.quote(self.redirect_uri, safe='')}"
            f"&state={self.state_encoded}"
            f"&authorization_session_id={self.authorization_session_id}"
        )
        password_url = (
            f"{AUTH}/password"
            f"?state={self.state_encoded}"
            f"&redirect_uri={urllib.parse.quote(self.redirect_uri, safe='')}"
            f"&authorization_session_id={self.authorization_session_id}"
        )
        try:
            self.s.get(
                signin_url,
                headers={
                    "user-agent": self._current_ua(),
                    "accept": "text/x-component",
                    "accept-language": "zh-CN,zh;q=0.9",
                    "next-action": NEXT_ACTION_SIGNIN_ENTRY,
                    "next-router-state-tree": "%5B%22%22%2C%7B%22children%22%3A%5B%22(main)%22%2C%7B%22children%22%3A%5B%22(root)%22%2C%7B%22children%22%3A%5B%22(sign-in)%22%2C%7B%22children%22%3A%5B%22__PAGE__%22%2C%7B%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%2Ctrue%5D",
                    "origin": AUTH,
                    "referer": signin_url,
                },
                allow_redirects=True,
            )
        except Exception:
            pass

        captcha_token = ""
        if captcha_solver:
            try:
                captcha_token = str(captcha_solver.solve_turnstile(AUTH, TURNSTILE_SITEKEY) or "").strip()
            except Exception:
                captcha_token = ""

        bd = _boundary()
        fields = [
            ("1_bot_detection_token", captcha_token),
            ("1_signals", _make_signals()),
            ("1_email", email),
            ("1_password", password),
            ("1_intent", "password"),
            ("1_redirect_uri", self.redirect_uri),
            ("1_authorization_session_id", self.authorization_session_id),
            ("1_state", self.state_raw),
            ("0", '["$K1"]'),
        ]
        body = _multipart(fields, bd)
        r = self.s.post(
            password_url,
            headers={
                "user-agent": self._current_ua(),
                "accept": "text/x-component",
                "accept-language": "zh-CN,zh;q=0.9",
                "content-type": f"multipart/form-data; boundary={bd}",
                "origin": AUTH,
                "referer": password_url,
                "next-action": NEXT_ACTION_SIGNIN_PASSWORD_POST,
                "next-router-state-tree": NEXT_ROUTER_STATE_TREE_SIGNIN_PASSWORD,
            },
            data=body,
            allow_redirects=False,
        )
        self._diag(
            f"signin-refresh post status={getattr(r,'status_code','')} "
            f"xredir={(r.headers.get('x-action-redirect','') or r.headers.get('location',''))[:160]}"
        )
        txt = getattr(r, "text", "") or ""
        loc = r.headers.get("x-action-redirect", "") or r.headers.get("location", "")
        if "/radar-challenge/send" in str(loc or ""):
            try:
                self._radar_send_url = urllib.parse.urljoin(AUTH, str(loc))
            except Exception:
                self._radar_send_url = str(loc or "")
        # 登录链路拿到新页面后，强制在 step5 重新提取 send action，避免复用旧值
        self._radar_send_action = ""
        um = re.search(r"user_[a-z0-9]{10,}", txt, flags=re.IGNORECASE)
        if um:
            self._user_id = um.group(0)
        pm = re.search(r"pendingAuthenticationToken[^\\n]{0,200}[\"']([^\"']{6,})[\"']", txt)
        if pm:
            self._pending_auth_token = pm.group(1)
        self.log(
            f"[Cursor][DEBUG] signin 刷新上下文完成: status={getattr(r, 'status_code', '')} "
            f"user_id={'Y' if self._user_id else 'N'} pending_len={len(self._pending_auth_token or '')}"
        )
        return bool(self._user_id and self._pending_auth_token)

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
        self._diag(
            f"step4 otp status={getattr(r,'status_code','')} "
            f"xredir={(r.headers.get('x-action-redirect','') or r.headers.get('location',''))[:180]}"
        )
        # 优先从 x-action-redirect/location 头里提取 code
        loc = r.headers.get("x-action-redirect", "") or r.headers.get("location", "")
        if "/radar-challenge/send" in str(loc or ""):
            try:
                self._radar_send_url = urllib.parse.urljoin(AUTH, str(loc))
            except Exception:
                self._radar_send_url = str(loc or "")
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

        def _pick_country_code(ds: str) -> str:
            # 常见国家码优先（按长度降序匹配），避免把 +447... 误切成 +4473
            known = [
                "886", "852", "853", "351",
                "971", "972", "973", "974", "975", "976",
                "86", "44", "1", "33", "34", "39", "49", "55", "61", "62", "63", "64", "65", "66", "7",
                "81", "82", "84", "90", "91", "92", "93", "94", "95", "98",
                "20", "27", "30", "31", "32", "36", "40", "41", "43", "45", "46", "47", "48",
            ]
            for cc in sorted(set(known), key=len, reverse=True):
                if ds.startswith(cc) and len(ds) > len(cc):
                    return cc
            # 最后兜底：不再贪婪取 4 位，优先 2~3 位，降低误判概率
            for n in (3, 2, 1):
                if len(ds) > n:
                    return ds[:n]
            return ""

        if raw.startswith("+"):
            cc = _pick_country_code(digits)
            if cc:
                country = f"+{cc}"
                national = digits[len(cc):]
            else:
                country = "+86"
                national = digits
        elif digits.startswith("86") and len(digits) >= 13:
            national = digits[2:]
            country = "+86"
        else:
            country = "+86"
            national = digits
        if not national:
            raise RuntimeError("手机号格式无效")
        e164 = f"{country}{national}"
        local = national
        if country == "+86" and len(national) == 11:
            local = f"({national[:3]}){national[3:7]}-{national[7:]}"
        elif country == "+44":
            # 英国手机号在本地输入通常带 trunk prefix 0（例如 07348xxxxxx）
            local = national if national.startswith("0") else f"0{national}"
        elif country in {"+1"} and len(national) >= 10:
            # 北美号段可读格式（不影响核心值）
            local = f"({national[:3]}){national[3:6]}-{national[6:]}"
        return country, local, e164

    def step5_send_phone_challenge(self, phone_number: str, state_encoded, captcha_solver=None):
        if not self.authorization_session_id:
            raise RuntimeError("缺少 authorization_session_id")
        if not self._pending_auth_token:
            raise RuntimeError("缺少 pending_authentication_token")
        if not self._user_id:
            self.log("[Cursor][DEBUG] user_id 缺失，继续尝试发送手机挑战（可能失败）")
        country_code, local_number, e164 = self._normalize_phone(phone_number)
        self._phone_number = e164
        bd = _boundary()
        default_send_url = (
            f"{AUTH}/radar-challenge/send"
            f"?user_id={urllib.parse.quote(self._user_id, safe='')}"
            f"&state={self.state_encoded}"
            f"&redirect_uri={urllib.parse.quote(self.redirect_uri, safe='')}"
            f"&authorization_session_id={self.authorization_session_id}"
        )
        # 兼容两种 send 形态：
        # 1) state/redirect_uri/authorization_session_id（注册链路常见）
        # 2) pending_authentication_token + user_id（登录后绑手机链路常见）
        send_candidates: list[str] = []
        if self._radar_send_url:
            send_candidates.append(self._radar_send_url)
        if self._pending_auth_token and self._user_id:
            send_candidates.append(
                f"{AUTH}/radar-challenge/send"
                f"?pending_authentication_token={urllib.parse.quote(self._pending_auth_token, safe='')}"
                f"&user_id={urllib.parse.quote(self._user_id, safe='')}"
            )
        send_candidates.append(default_send_url)
        # 去重并保持顺序
        _seen = set()
        send_candidates = [u for u in send_candidates if u and not (u in _seen or _seen.add(u))]
        self._diag(f"step5 send_candidates={len(send_candidates)}")

        send_url = ""
        fallback_from_radar_page = False
        # Step5 前先预热 radar-challenge/send 页面，并动态提取 next-action；选择最匹配的一条 send_url
        try:
            for idx, cand in enumerate(send_candidates, start=1):
                next_url = "/radar-challenge/send"
                pu = urllib.parse.urlparse(cand)
                if pu.path:
                    next_url = pu.path + (f"?{pu.query}" if pu.query else "")
                r_pre = self.s.get(
                    cand,
                    headers={
                        "user-agent": self._current_ua(),
                        "accept": "text/x-component",
                        "accept-language": "zh-CN,zh;q=0.9",
                        "referer": cand,
                        "origin": AUTH,
                        "rsc": "1",
                        "next-url": next_url,
                    },
                    allow_redirects=True,
                )
                self._diag(
                    f"step5 preheat#{idx} status={getattr(r_pre,'status_code','')} "
                    f"url={getattr(r_pre,'url','')} cand={cand}"
                )
                final_url = str(getattr(r_pre, "url", "") or "")
                pre_txt = getattr(r_pre, "text", "") or ""
                hid_user, hid_pending = self._extract_radar_hidden_fields(pre_txt)
                if hid_user and hid_user != self._user_id:
                    self._diag(f"step5 preheat#{idx} refresh user_id from page")
                    self._user_id = hid_user
                if hid_pending and hid_pending != self._pending_auth_token:
                    self._diag(f"step5 preheat#{idx} refresh pending token from page")
                    self._pending_auth_token = hid_pending
                act = self._extract_action_id(pre_txt, prefer_ids=[NEXT_ACTION_RADAR_SEND])
                if not act:
                    act = self._extract_action_id_from_headers(
                        getattr(r_pre, "headers", None),
                        prefer_ids=[NEXT_ACTION_RADAR_SEND],
                    )
                if act:
                    send_url = cand
                    self._radar_send_action = act
                    self.log(f"[Cursor][DEBUG] step5_send 预热命中候选#{idx}: action={act[:12]}...")
                    break
                # 软门槛：RSC 已明确处于 radar send 页面时，允许回退固定 action 继续尝试
                in_radar_page = (
                    "/radar-challenge/send" in final_url
                    and "radar-challenge" in pre_txt
                    and "\"send\"" in pre_txt
                )
                if in_radar_page:
                    send_url = cand
                    self._radar_send_action = NEXT_ACTION_RADAR_SEND
                    fallback_from_radar_page = True
                    self.log(f"[Cursor][DEBUG] step5_send 候选#{idx} 未提取到 next-action，已回退固定 action")
                    self._diag(f"step5 preheat#{idx} fallback_action={NEXT_ACTION_RADAR_SEND[:12]}...")
                    break
                self.log(f"[Cursor][DEBUG] step5_send 候选#{idx} 未提取到 next-action")
                if pre_txt:
                    self.log(f"[Cursor][DEBUG] step5_send 候选#{idx} body snippet={pre_txt[:180].replace(chr(10), ' ')}")
            if not send_url:
                self._radar_send_action = ""
                raise RuntimeError("手机号挑战发送失败: 未提取到 radar send next-action")
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"手机号挑战发送失败: 预热 radar 页面失败 {e}")
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
        used_action = self._radar_send_action
        if not used_action:
            raise RuntimeError("手机号挑战发送失败: 缺少 radar send next-action")
        self._diag(f"step5 selected_send_url={send_url}")
        if fallback_from_radar_page:
            self._diag("step5 using fixed radar send action fallback")
        action_candidates: list[str] = []
        for a in (
            used_action,
            NEXT_ACTION_RADAR_SEND,
            self._next_action,
            NEXT_ACTION_PASSWORD_POST,
        ):
            av = str(a or "").strip()
            if av and av not in action_candidates:
                action_candidates.append(av)
        self._diag(f"step5 action_candidates={len(action_candidates)}")
        if not self._has_cf_clearance_cookie():
            self.log("[Cursor][DEBUG] 当前会话缺少 cf_clearance")
            self._try_fetch_cf_assets_with_captcha5s(captcha_solver=captcha_solver, target_url=send_url)
            if not self._has_cf_clearance_cookie():
                self.log("[Cursor][DEBUG] 协议模式未拿到 cf_clearance（已禁用浏览器手动采集）")
        removed = self._dedupe_session_cookies()
        if removed:
            self.log(f"[Cursor][DEBUG] step5_send cookies 去重完成: removed={removed}")
        try:
            all_names = [str(getattr(c, "name", "") or "") for c in getattr(self.s.cookies, "jar", []) or []]
            focus_names = [n for n in all_names if ("cf" in n.lower()) or ("state" in n.lower()) or ("workos" in n.lower()) or ("rcid" in n.lower())]
            self.log(f"[Cursor][DEBUG] step5_send cookie_names={focus_names[:30]}")
        except Exception:
            pass
        # invalid_params 时，同一号码尝试几种 local_number 形态（不换号）
        payload_variants: list[tuple[str, str, str]] = [(country_code, local_number, e164)]
        if country_code == "+44":
            national_digits = re.sub(r"\D+", "", e164)
            if national_digits.startswith("44"):
                national_digits = national_digits[2:]
            local_no0 = national_digits
            local_with0 = national_digits if national_digits.startswith("0") else f"0{national_digits}"
            if len(local_no0) >= 10:
                local_pretty = f"({local_no0[:3]}){local_no0[3:6]}-{local_no0[6:]}"
            else:
                local_pretty = local_no0
            for lv in (local_no0, local_with0, local_pretty):
                item = (country_code, lv, e164)
                if item not in payload_variants:
                    payload_variants.append(item)
        # radar 默认不走 proxy（代理出口经常触发 radar_sms_challenge_error）
        _old_proxies = getattr(self.s, "proxies", None)
        if (not self._radar_use_proxy) and _old_proxies:
            try:
                self.s.proxies = {}
            except Exception:
                pass
        r = None
        txt = ""
        used_action_final = used_action
        try:
            for idx, (cc, local_v, e164_v) in enumerate(payload_variants, start=1):
                fields_try = [
                    ("1_country_code", cc),
                    ("1_local_number", local_v),
                    ("1_phone_number", e164_v),
                    ("1_redirect_uri", self.redirect_uri),
                    ("1_authorization_session_id", self.authorization_session_id),
                    ("1_state", self.state_raw),
                    ("1_user_id", self._user_id),
                    ("1_pending_authentication_token", self._pending_auth_token),
                    ("0", '["$K1"]'),
                ]
                self.log(
                    f"[Cursor][DEBUG] step5_send payload#{idx} country_code={cc} "
                    f"local_number={local_v} phone_number={e164_v}"
                )
                body = _multipart(fields_try, bd)
                matched = False
                for act_i, act in enumerate(action_candidates, start=1):
                    self.log(f"[Cursor][DEBUG] step5_send using next-action={act[:12]}... (payload#{idx}/action#{act_i})")
                    r = self.s.post(
                        send_url,
                        headers=self._radar_common_headers(
                            referer=send_url,
                            boundary=bd,
                            next_action=act,
                            state_tree=NEXT_ROUTER_STATE_TREE_RADAR_SEND,
                        ),
                        data=body,
                        allow_redirects=False,
                    )
                    self._diag(
                        f"step5 post#{idx} action#{act_i} status={getattr(r,'status_code','')} "
                        f"xredir={(r.headers.get('x-action-redirect','') or r.headers.get('location',''))[:160]}"
                    )
                    txt = getattr(r, "text", "") or ""
                    # 命中条件：
                    # 1) 直接拿到 verification_id
                    # 2) 返回了明确 code（如 radar_sms_challenge_error / invalid_params），说明 action 生效
                    has_vid = bool(self._extract_verification_id(txt))
                    has_code = bool(re.search(r'"code"\s*:\s*"[^"]+"', txt))
                    if has_vid or has_code:
                        used_action_final = act
                        matched = True
                        break
                if '"code":"invalid_params"' in txt.replace(" ", "") and idx < len(payload_variants):
                    self.log(f"[Cursor][DEBUG] step5_send payload#{idx} 命中 invalid_params，尝试下一个格式...")
                    continue
                # 若 action 轮询都未命中明确结果，也结束本 payload，后续走 second/third fire 兜底
                if matched or idx == len(payload_variants):
                    break
        finally:
            if (not self._radar_use_proxy) and _old_proxies:
                try:
                    self.s.proxies = _old_proxies
                except Exception:
                    pass
        txt = txt or (getattr(r, "text", "") or "")
        self._diag(f"step5 chosen_action_final={used_action_final[:12]}...")
        hid_user, hid_pending = self._extract_radar_hidden_fields(txt)
        if hid_user and hid_user != self._user_id:
            self._diag("step5 post#1 refresh user_id from response")
            self._user_id = hid_user
        if hid_pending and hid_pending != self._pending_auth_token:
            self._diag("step5 post#1 refresh pending token from response")
            self._pending_auth_token = hid_pending
        self._diag_dump_text("step5_post1", txt)
        # 调试：记录发送手机验证码这一跳的返回，方便定位 verification_id 位置
        try:
            loc = r.headers.get("x-action-redirect", "") or r.headers.get("location", "") or ""
        except Exception:
            loc = ""
        # 进一步调试：确认 CF cookie 是否在 session 中（纯协议经常因为缺 clearance 被拦）
        try:
            cookie_names = [str(getattr(c, "name", "") or "") for c in getattr(self.s.cookies, "jar", []) or []]
        except Exception:
            cookie_names = []
        has_clearance = "cf_clearance" in cookie_names
        has_bm = "__cf_bm" in cookie_names
        proxy_on = bool(getattr(self.s, "proxies", None))
        self.log(
            f"[Cursor][DEBUG] step5_send ctx user_id={'Y' if self._user_id else 'N'} "
            f"pending_token_len={len(self._pending_auth_token or '')} "
            f"cf_clearance={'Y' if has_clearance else 'N'} __cf_bm={'Y' if has_bm else 'N'} "
            f"proxy={'Y' if proxy_on else 'N'} radar_use_proxy={'Y' if self._radar_use_proxy else 'N'} "
            f"ua={'browser' if self._browser_ua else 'static'}"
        )
        # 没有 cf_clearance 时，Radar/CF 很容易直接拒绝发短信；提前提示，避免继续等待短信
        allow_no_clearance = str((dict(self.__dict__).get("_allow_no_clearance") or "")).strip()
        # 兼容从 extra 里传 cursor_allow_no_clearance=true
        try:
            allow_no_clearance = allow_no_clearance or ("1" if str(getattr(self, "_allow_no_clearance_flag", "")).strip() else "")
        except Exception:
            pass
        if not has_clearance and str(allow_no_clearance).strip().lower() not in ("1", "true", "yes", "on"):
            self.log("[Cursor][DEBUG] step5_send 缺少 cf_clearance，Radar 可能会拒绝发短信（radar_sms_challenge_error）")
        self.log(
            f"[Cursor][DEBUG] step5_send POST status={getattr(r, 'status_code', '')} "
            f"redirect={str(loc)[:160]}"
        )
        if txt:
            self.log(f"[Cursor][DEBUG] step5_send body snippet={txt[:220].replace(chr(10), ' ')}")
            # 如果是 radar_sms_challenge_error，单独提取出来方便看
            try:
                em = re.search(r'"code"\\s*:\\s*"([^"]+)"', txt)
                mm = re.search(r'"message"\\s*:\\s*"([^"]+)"', txt)
                if em or mm:
                    self.log(f"[Cursor][DEBUG] step5_send err code={em.group(1) if em else ''} msg={mm.group(1) if mm else ''}")
            except Exception:
                pass

        self._phone_verification_id = self._extract_verification_id(txt)
        # 某些场景首个 POST 只返回 send 页面 RSC（未包含 verification_id），可在同上下文下再触发一次
        need_second_fire = (
            (not self._phone_verification_id)
            and ("radar-challenge" in (txt or ""))
            and ("\"send\"" in (txt or ""))
        )
        if need_second_fire:
            self._diag("step5 first post looks like send-page RSC, retrying one more fire")
            body2 = _multipart([
                ("1_country_code", country_code),
                ("1_local_number", local_number),
                ("1_phone_number", e164),
                ("1_redirect_uri", self.redirect_uri),
                ("1_authorization_session_id", self.authorization_session_id),
                ("1_state", self.state_raw),
                ("1_user_id", self._user_id),
                ("1_pending_authentication_token", self._pending_auth_token),
                ("0", '["$K1"]'),
            ], bd)
            r2 = self.s.post(
                send_url,
                headers=self._radar_common_headers(
                    referer=send_url,
                    boundary=bd,
                    next_action=used_action,
                    state_tree=NEXT_ROUTER_STATE_TREE_RADAR_SEND,
                ),
                data=body2,
                allow_redirects=False,
            )
            txt2 = getattr(r2, "text", "") or ""
            hid_user2, hid_pending2 = self._extract_radar_hidden_fields(txt2)
            if hid_user2 and hid_user2 != self._user_id:
                self._diag("step5 post#2 refresh user_id from response")
                self._user_id = hid_user2
            if hid_pending2 and hid_pending2 != self._pending_auth_token:
                self._diag("step5 post#2 refresh pending token from response")
                self._pending_auth_token = hid_pending2
            self._diag_dump_text("step5_post2", txt2)
            self._diag(
                f"step5 second-fire status={getattr(r2,'status_code','')} "
                f"xredir={(r2.headers.get('x-action-redirect','') or r2.headers.get('location',''))[:160]}"
            )
            if txt2:
                self.log(f"[Cursor][DEBUG] step5_send second-fire body snippet={txt2[:220].replace(chr(10), ' ')}")
            self._phone_verification_id = self._extract_verification_id(txt2) or self._phone_verification_id
            txt = txt2 or txt
        # third-fire: 按登录后绑手机链路，改用 pending_token+user_id URL 再触发一次
        if (not self._phone_verification_id) and self._pending_auth_token and self._user_id:
            alt_send_url = (
                f"{AUTH}/radar-challenge/send"
                f"?pending_authentication_token={urllib.parse.quote(self._pending_auth_token, safe='')}"
                f"&user_id={urllib.parse.quote(self._user_id, safe='')}"
                f"&state={self.state_encoded}"
                f"&redirect_uri={urllib.parse.quote(self.redirect_uri, safe='')}"
                f"&authorization_session_id={self.authorization_session_id}"
            )
            if alt_send_url != send_url:
                self._diag(f"step5 third-fire switching url={alt_send_url}")
                body3 = _multipart([
                    ("1_country_code", country_code),
                    ("1_local_number", local_number),
                    ("1_phone_number", e164),
                    ("1_redirect_uri", self.redirect_uri),
                    ("1_authorization_session_id", self.authorization_session_id),
                    ("1_state", self.state_raw),
                    ("1_user_id", self._user_id),
                    ("1_pending_authentication_token", self._pending_auth_token),
                    ("0", '["$K1"]'),
                ], bd)
                r3 = self.s.post(
                    alt_send_url,
                    headers=self._radar_common_headers(
                        referer=alt_send_url,
                        boundary=bd,
                        next_action=used_action,
                        state_tree=NEXT_ROUTER_STATE_TREE_RADAR_SEND,
                    ),
                    data=body3,
                    allow_redirects=False,
                )
                txt3 = getattr(r3, "text", "") or ""
                hid_user3, hid_pending3 = self._extract_radar_hidden_fields(txt3)
                if hid_user3 and hid_user3 != self._user_id:
                    self._diag("step5 post#3 refresh user_id from response")
                    self._user_id = hid_user3
                if hid_pending3 and hid_pending3 != self._pending_auth_token:
                    self._diag("step5 post#3 refresh pending token from response")
                    self._pending_auth_token = hid_pending3
                self._diag_dump_text("step5_post3", txt3)
                self._diag(
                    f"step5 third-fire status={getattr(r3,'status_code','')} "
                    f"xredir={(r3.headers.get('x-action-redirect','') or r3.headers.get('location',''))[:160]}"
                )
                if txt3:
                    self.log(f"[Cursor][DEBUG] step5_send third-fire body snippet={txt3[:220].replace(chr(10), ' ')}")
                self._phone_verification_id = self._extract_verification_id(txt3) or self._phone_verification_id
                txt = txt3 or txt
        if not self._phone_verification_id:
            self.log("[Cursor][DEBUG] step5_send 未提取到 verification_id")
            # 发短信挑战失败时直接中断，避免继续进入 Step6 无意义等待接码
            err_code = ""
            err_msg = ""
            try:
                em = re.search(r'"code"\s*:\s*"([^"]+)"', txt)
                mm = re.search(r'"message"\s*:\s*"([^"]+)"', txt)
                err_code = em.group(1) if em else ""
                err_msg = mm.group(1) if mm else ""
            except Exception:
                pass
            if err_code or err_msg:
                if str(err_code).strip() == "radar_sms_challenge_error" and not has_clearance:
                    raise RuntimeError(
                        "手机号挑战发送失败: radar_sms_challenge_error（缺少 cf_clearance，建议从浏览器导入 cursor_cf_clearance 后重试）"
                    )
                raise RuntimeError(f"手机号挑战发送失败: {err_code or 'unknown_error'} {err_msg}".strip())
            raise RuntimeError("手机号挑战发送失败: 未返回 verification_id")

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
        _old_proxies = getattr(self.s, "proxies", None)
        if (not self._radar_use_proxy) and _old_proxies:
            try:
                self.s.proxies = {}
            except Exception:
                pass
        removed = self._dedupe_session_cookies()
        if removed:
            self.log(f"[Cursor][DEBUG] step6_verify cookies 去重完成: removed={removed}")
        try:
            r = self.s.post(
                verify_url,
                headers=self._radar_common_headers(
                    referer=verify_url,
                    boundary=bd,
                    next_action=NEXT_ACTION_RADAR_VERIFY,
                    state_tree=NEXT_ROUTER_STATE_TREE_RADAR_VERIFY,
                ),
                data=body,
                allow_redirects=False,
            )
            self._diag(
                f"step6 verify status={getattr(r,'status_code','')} "
                f"xredir={(r.headers.get('x-action-redirect','') or r.headers.get('location',''))[:180]}"
            )
        finally:
            if (not self._radar_use_proxy) and _old_proxies:
                try:
                    self.s.proxies = _old_proxies
                except Exception:
                    pass
        loc = r.headers.get("x-action-redirect", "") or r.headers.get("location", "")
        m = re.search(r"code=([^&]+)", loc)
        if m:
            self._phone_verified = True
            return m.group(1)
        txt = getattr(r, "text", "") or ""
        m2 = re.search(r'code=([^&"\'\\s]+)', txt)
        if m2:
            self._phone_verified = True
            return m2.group(1)
        return ""

    def step7_get_token(self, auth_code, state_encoded, captcha_solver=None):
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

        # 手机号验证后，继续补一次 5 秒盾并预热 authenticator
        # 避免后续链路（包括 callback 写 cookie）被 Cloudflare 拦截
        try:
            if self._phone_verified:
                self._post_phone_verify_prewarm(captcha_solver=captcha_solver)
        except Exception:
            pass

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
        self._diag(
            f"step7 callback#1 status={getattr(r,'status_code','')} "
            f"loc={(r.headers.get('location','') or r.headers.get('x-action-redirect',''))[:180]}"
        )
        token = _extract_from_cookies()
        if token:
            return token

        r2 = self.s.get(
            url,
            headers={"user-agent": UA, "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"},
            allow_redirects=True,
        )
        self._diag(f"step7 callback#2 status={getattr(r2,'status_code','')} final={getattr(r2,'url','')}")
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
