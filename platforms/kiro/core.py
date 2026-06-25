"""
Kiro / AWS Builder ID Auto-Registration core
Protocol-only registration flow:
  Step 1:  Kiro InitiateLogin (CBOR)
  Step 2:  Redirect chain → signin.aws wsh
  Step 3:  signin.aws → SIGNUP action
  Step 4:  signup flow → profile.aws redirect
  Step 5:  TES token (awsd2c-token)
  Step 6:  profile.aws page load + /api/start
  Step 7:  send-otp
  Step 8:  create-identity (OTP verify)
  Step 9:  signup registration (registrationCode)
  Step 10: Set password (JWE encryption)
  Step 11: Final login
  Step 12: OIDC Auth Code Flow → accessToken + sessionToken
  Step 12f: OIDC Device Auth Flow → refreshToken
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import random
import re
import secrets
import string
import struct
import time
import uuid
from urllib.parse import parse_qs, quote as url_quote, unquote as url_unquote, urlencode, urlparse

import cbor2
from curl_cffi import requests as curl_requests
from jwcrypto import jwk, jwe

KIRO = "https://app.kiro.dev"
SIGNIN = "https://us-east-1.signin.aws"
DIR_ID = "d-9067642ac7"
PROFILE = "https://profile.aws.amazon.com"
PORTAL_SSO = "https://portal.sso.us-east-1.amazonaws.com"
OIDC = "https://oidc.us-east-1.amazonaws.com"

UA = {
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/131.0.0.0 Safari/537.36",
    "sec-ch-ua": '"Chromium";v="131", "Not_A Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "dnt": "1",
}

XXTEA_KEY = [1888420705, 2576816180, 2347232058, 874813317]
XXTEA_DELTA = 0x9E3779B9
_u32 = lambda x: x & 0xFFFFFFFF

GPU_EXT = [
    "ANGLE_instanced_arrays", "EXT_blend_minmax", "EXT_clip_control",
    "EXT_color_buffer_half_float", "EXT_depth_clamp",
    "EXT_disjoint_timer_query", "EXT_float_blend", "EXT_frag_depth",
    "EXT_polygon_offset_clamp", "EXT_shader_texture_lod",
    "EXT_texture_compression_bptc", "EXT_texture_compression_rgtc",
    "EXT_texture_filter_anisotropic", "EXT_texture_mirror_clamp_to_edge",
    "EXT_sRGB", "KHR_parallel_shader_compile", "OES_element_index_uint",
    "OES_fbo_render_mipmap", "OES_standard_derivatives", "OES_texture_float",
    "OES_texture_float_linear", "OES_texture_half_float",
    "OES_texture_half_float_linear", "OES_vertex_array_object",
    "WEBGL_blend_func_extended", "WEBGL_color_buffer_float",
    "WEBGL_compressed_texture_astc", "WEBGL_compressed_texture_etc",
    "WEBGL_compressed_texture_etc1", "WEBGL_compressed_texture_pvrtc",
    "WEBGL_compressed_texture_s3tc", "WEBGL_compressed_texture_s3tc_srgb",
    "WEBGL_debug_renderer_info", "WEBGL_debug_shaders",
    "WEBGL_depth_texture", "WEBGL_draw_buffers", "WEBGL_lose_context",
    "WEBGL_multi_draw", "WEBGL_polygon_mode",
]

REAL_HIST = [
    13847, 42, 42, 40, 62, 33, 47, 29, 41, 37, 32, 25, 27, 53, 23, 22, 31, 20, 24,
    30, 34, 20, 37, 15, 21, 32, 25, 26, 66, 25, 16, 27, 26, 19, 22, 32, 38, 15, 39,
    35, 49, 9, 29, 43, 16, 26, 23, 15, 29, 30, 36, 46, 18, 29, 11, 30, 24, 27, 20,
    27, 22, 19, 20, 38, 171, 32, 25, 33, 15, 15, 6, 22, 11, 39, 31, 24, 18, 12, 17,
    34, 17, 30, 17, 27, 25, 28, 20, 19, 19, 19, 24, 34, 10, 24, 14, 27, 28, 18, 31,
    27, 78, 28, 512, 41, 28, 22, 34, 15, 26, 29, 34, 16, 17, 21, 17, 43, 17, 9, 24,
    34, 17, 14, 26, 6, 20, 39, 28, 25, 230, 20, 44, 19, 8, 24, 18, 12, 28, 16, 5,
    28, 37, 21, 11, 27, 22, 30, 18, 16, 25, 18, 11, 25, 30, 104, 13, 38, 22, 22,
    42, 18, 23, 22, 32, 9, 30, 18, 5, 31, 34, 18, 24, 17, 22, 25, 12, 16, 34, 18,
    28, 23, 15, 55, 45, 18, 21, 31, 21, 28, 22, 21, 31, 30, 145, 29, 19, 34, 18,
    21, 24, 37, 30, 19, 49, 34, 62, 62, 23, 24, 21, 40, 27, 30, 37, 22, 38, 51, 40,
    37, 29, 27, 53, 28, 31, 27, 37, 36, 40, 57, 31, 22, 41, 32, 23, 35, 28, 58, 41,
    45, 27, 38, 36, 48, 49, 30, 37, 78, 56, 36, 40, 62, 48, 81, 70, 59, 94, 13740,
]


def _xxtea_enc(data_str: str | bytes, key: list[int]) -> bytes:
    raw = data_str.encode("latin-1") if isinstance(data_str, str) else data_str
    while len(raw) % 4 != 0:
        raw += b"\x00"
    n = len(raw) // 4
    if n < 2:
        raw += b"\x00" * 4
        n = 2
    v = list(struct.unpack(f"<{n}I", raw))
    rounds = 6 + 52 // n
    s = v[n - 1]
    c = 0
    for _ in range(rounds):
        c = _u32(c + XXTEA_DELTA)
        u = (c >> 2) & 3
        for d in range(n):
            nx = v[(d + 1) % n]
            mx = _u32(_u32(_u32(s >> 5) ^ _u32(nx << 2)) + _u32(_u32(nx >> 3) ^ _u32(s << 4)))
            mx = _u32(mx ^ _u32(_u32(c ^ nx) + _u32(key[(3 & d) ^ u] ^ s)))
            v[d] = _u32(v[d] + mx)
            s = v[d]
    return b"".join(struct.pack("<I", x) for x in v)


def _gen_perf(nav_start: int) -> dict:
    dns = nav_start + random.randint(30, 40)
    conn = dns
    conn_end = dns + random.randint(1, 3)
    req = conn_end + random.randint(0, 2)
    resp_s = req + random.randint(250, 350)
    resp_e = resp_s
    dom_load = resp_e + random.randint(2, 5)
    dom_int = dom_load + random.randint(2800, 3500)
    dom_cl_s = dom_int
    dom_cl_e = dom_int
    dom_comp = dom_cl_e + random.randint(800, 1200)
    load_s = dom_comp
    load_e = dom_comp
    return {
        "connectStart": conn, "secureConnectionStart": conn,
        "unloadEventEnd": 0, "domainLookupStart": dns,
        "domainLookupEnd": dns, "responseStart": resp_s,
        "connectEnd": conn_end, "responseEnd": resp_e,
        "requestStart": req, "domLoading": dom_load,
        "redirectStart": 0, "loadEventEnd": load_e,
        "domComplete": dom_comp, "navigationStart": nav_start,
        "loadEventStart": load_s,
        "domContentLoadedEventEnd": dom_cl_e,
        "unloadEventStart": 0, "redirectEnd": 0,
        "domInteractive": dom_int, "fetchStart": dns,
        "domContentLoadedEventStart": dom_cl_s,
    }


def gen_fwcim(location_url: str, ubid_main: str, canvas_hash: int | None = None) -> str:
    now_ms = int(time.time() * 1000)
    nav_start = now_ms - random.randint(3500, 5000)
    if canvas_hash is None:
        canvas_hash = random.randint(1000000000, 2147483647)
    plugins = (
        "PDF Viewer Chrome PDF Viewer Chromium PDF Viewer "
        "Microsoft Edge PDF Viewer WebKit built-in PDF "
        "||1440-900-900-30-*-*-*"
    )
    data = {
        "metrics": {"el": 0, "script": 0, "h": 0, "batt": 0, "perf": 0, "auto": 0,
                     "tz": 0, "fp2": 0, "lsubid": 1, "browser": 0, "capabilities": 0,
                     "gpu": 0, "dnt": 0, "math": 0, "tts": 0, "input": 0, "canvas": 0,
                     "captchainput": 0, "pow": 0},
        "start": now_ms - random.randint(20, 60),
        "interaction": {"clicks": 0, "touches": 0, "keyPresses": 0, "cuts": 0,
                         "copies": 0, "pastes": 0, "keyPressTimeIntervals": [],
                         "mouseClickPositions": [], "keyCycles": [], "mouseCycles": [],
                         "touchCycles": []},
        "scripts": {"dynamicUrls": ["/assets/js/app.js"], "inlineHashes": [],
                     "elapsed": 0, "dynamicUrlCount": 1, "inlineHashesCount": 0},
        "history": {"length": random.randint(2, 8)},
        "battery": {},
        "performance": {"timing": _gen_perf(nav_start)},
        "automation": {"wd": {"properties": {"document": [], "window": [], "navigator": []}},
                        "phantom": {"properties": {"window": []}}},
        "end": now_ms,
        "timeZone": 8,
        "flashVersion": None,
        "plugins": plugins, "dupedPlugins": plugins,
        "screenInfo": "1440-900-900-30-*-*-*",
        "lsUbid": f"X{ubid_main}:{now_ms // 1000}",
        "referrer": "https://view.awsapps.com/",
        "userAgent": UA["user-agent"],
        "location": location_url,
        "webDriver": False,
        "capabilities": {
            "css": {"textShadow": 1, "WebkitTextStroke": 1, "boxShadow": 1,
                     "borderRadius": 1, "borderImage": 1, "opacity": 1,
                     "transform": 1, "transition": 1},
            "js": {"audio": True, "geolocation": True, "localStorage": "supported",
                    "touch": False, "video": True, "webWorker": True},
            "elapsed": 0,
        },
        "gpu": {"vendor": "Google Inc. (Apple)",
                 "model": "ANGLE (Apple, ANGLE Metal Renderer: Apple M4, "
                          "Unspecified Version)",
                 "extensions": GPU_EXT},
        "dnt": None,
        "math": {"tan": "-1.4214488238747245",
                  "sin": "0.8178819121159085", "cos": "-0.5753861119575491"},
        "form": {},
        "canvas": {"hash": canvas_hash, "emailHash": None, "histogramBins": REAL_HIST},
        "token": {"isCompatible": False, "pageHasCaptcha": 0},
        "auth": {"form": {"method": "get"}},
        "errors": [],
        "version": "4.0.0",
    }
    js = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    crc = format(binascii.crc32(js.encode()) & 0xFFFFFFFF, "08X")
    plain = crc + "#" + js
    enc = _xxtea_enc(plain, XXTEA_KEY)
    b64 = base64.b64encode(enc).decode().rstrip("=")
    return "ECdITeCs:" + b64


def encrypt_password_jwe(password: str, public_key_jwk: dict) -> str:
    key = jwk.JWK(**public_key_jwk)
    protected = json.dumps({
        "alg": "RSA-OAEP-256",
        "kid": public_key_jwk["kid"],
        "enc": "A256GCM",
        "cty": "enc",
        "typ": "application/aws+signin+jwe",
    }, separators=(",", ":"))
    now = int(time.time())
    plaintext = json.dumps({
        "iss": "us-east-1.signin",
        "iat": now,
        "nbf": now,
        "jti": str(uuid.uuid4()),
        "exp": now + 300,
        "aud": "us-east-1.AWSPasswordService",
        "password": password,
    }, separators=(",", ":"))
    token = jwe.JWE(plaintext.encode("utf-8"), recipient=key, protected=protected)
    return token.serialize(compact=True)


def _pkce() -> tuple[str, str]:
    v = secrets.token_urlsafe(43)
    c = base64.urlsafe_b64encode(hashlib.sha256(v.encode()).digest()).rstrip(b"=").decode()
    return v, c


def _vid() -> str:
    t = int(time.time() * 1000)
    r = "".join(random.choices(string.ascii_lowercase + string.digits, k=12))
    return f"{t}-{r}"


def _pwd() -> str:
    return secrets.token_urlsafe(12) + "!A1"


def _uuid() -> str:
    return str(uuid.uuid4())


def _ubid() -> str:
    return f"{random.randint(100, 999)}-{random.randint(1000000, 9999999)}-{random.randint(1000000, 9999999)}"


class KiroRegister:
    def __init__(self, proxy: str | None = None, tag: str = "REG"):
        self.tag = tag
        self.proxy = proxy
        self.s = curl_requests.Session(impersonate="safari17_0")
        if proxy:
            self.s.proxies = {"https": proxy, "http": proxy}
        self.cv, self.cc = _pkce()
        self.state = _uuid()
        self.vid = _vid()
        self._platform_ubid = _ubid()
        self._profile_ubid = _ubid()
        self._canvas_hash = random.randint(1000000000, 2147483647)

        # Step state
        self.wsh = None
        self.sid = None
        self._login_wsh = None
        self._signup_wsh = None
        self._aws_ubid_main = None
        self._awsd2c_token = None
        self._tes_visitor_id = None
        self._profile_load_ts = None
        self._profile_wf_id = None
        self._profile_wf_state = None

        # Step 12 data
        self._portal_csrf_token = None
        self._orchestrator_id = None
        self._callback_url = None
        self._workflow_result_handle = None
        self._step11_state = None
        self._step12_redirect_url = None

        # SSO session token (stc) from aws-usi-authn cookie, saved early
        # before cookie cleaning deletes it in step 10
        self._ssosession_token = ""

    def log(self, msg: str) -> None:
        print(f"[{self.tag}] {msg}")

    # ── Cookie management ──

    def _capture_cookies(self, resp) -> None:
        hostname = urlparse(str(resp.url)).hostname or "us-east-1.signin.aws"
        for k, v in resp.headers.multi_items():
            if k.lower() != "set-cookie":
                continue
            m = re.match(r"([^=]+)=([^;]*)", v)
            if not m:
                continue
            name, value = m.group(1), m.group(2)
            dm = re.search(r"[Dd]omain=([^;,\s]+)", v)
            pm = re.search(r"[Pp]ath=([^;,\s]+)", v)
            path = pm.group(1) if pm else "/"
            if name == "aws-ubid-main":
                self._aws_ubid_main = value
            # Capture raw SSO session token (stc) from Set-Cookie header
            # BEFORE it passes through curl_cffi's cookie jar (which corrupts it).
            if name == "aws-usi-authn":
                raw_header_val = value
                # Server URL-encodes `=` as `%3D` in cookie values
                raw_b64 = url_unquote(raw_header_val)
                try:
                    missing = (4 - (len(raw_b64) % 4)) % 4
                    padded = raw_b64 + "=" * missing
                    decoded = base64.b64decode(padded).decode("utf-8")
                    parsed = json.loads(decoded)
                    stc_val = parsed.get("stc", "")
                    if stc_val:
                        self._ssosession_token = stc_val
                        self.log(f"  ★ Captured SSO session token from raw header: {stc_val[:50]}...")
                except Exception as ex:
                    self.log(f"  ⚠️ Could not decode aws-usi-authn from raw header: {ex}")
            if dm:
                domain = dm.group(1).lstrip(".")
                dot_domain = "." + domain
                try:
                    self.s.cookies.delete(name, domain=dot_domain, path=path)
                except Exception:
                    pass
                self.s.cookies.set(name, value, domain=domain, path=path)
            else:
                self.s.cookies.set(name, value, domain=hostname, path=path)

    def _setup_signin_js_cookies(self) -> None:
        domain = "us-east-1.signin.aws"
        try:
            self.s.cookies.delete("platform-ubid", domain=domain, path="/platform")
        except Exception:
            pass
        self.s.cookies.set("platform-ubid", self._platform_ubid, domain=domain, path="/platform")

    def _update_directory_csrf_with_signup(self) -> None:
        from urllib.parse import unquote as url_unquote
        domain = "us-east-1.signin.aws"
        wf_by_domain = {}
        dir_by_domain = {}
        dir_csrf_path = f"/platform/{DIR_ID}"
        for c in self.s.cookies.jar:
            if "signin.aws" not in (c.domain or ""):
                continue
            if c.name == "workflow-csrf-token":
                wf_by_domain[c.domain] = c.value
            elif c.name == "directory-csrf-token":
                dir_by_domain[c.domain] = (c.value, c.path)
        wf_csrf_val = wf_by_domain.get(domain) or wf_by_domain.get(f".{domain}")
        dir_entry = dir_by_domain.get(domain) or dir_by_domain.get(f".{domain}")
        dir_csrf_val = dir_entry[0] if dir_entry else None
        if dir_entry:
            dir_csrf_path = dir_entry[1] or dir_csrf_path
        if not wf_csrf_val or not dir_csrf_val:
            self.log(f"  ⚠️ _update_directory_csrf: wf={wf_csrf_val is not None} dir={dir_csrf_val is not None}")
            return
        try:
            wf_decoded = json.loads(url_unquote(wf_csrf_val))
            dir_decoded = json.loads(url_unquote(dir_csrf_val))
            signup_token = wf_decoded.get("signupCsrfToken")
            if signup_token and "signupCsrfToken" not in dir_decoded:
                dir_decoded["signupCsrfToken"] = signup_token
                new_val = url_quote(json.dumps(dir_decoded, separators=(",", ":")), safe="")
                for c in list(self.s.cookies.jar):
                    if c.name == "directory-csrf-token":
                        try:
                            self.s.cookies.delete(c.name, domain=c.domain, path=c.path)
                        except Exception:
                            pass
                self.s.cookies.set("directory-csrf-token", new_val, domain=domain, path=dir_csrf_path)
                self.log(f"  ★ directory-csrf-token added signupCsrfToken={signup_token[:12]}")
            elif signup_token:
                self.log("  ★ directory-csrf-token already has signupCsrfToken, skipping")
        except Exception as e:
            self.log(f"  ⚠️ Failed to update directory-csrf-token: {e}")

    def _clean_non_bare_domain_cookies(self) -> int:
        cleanup_domains = [".us-east-1.signin.aws", ".signin.aws", "signin.aws"]
        cleaned = 0
        for c in list(self.s.cookies.jar):
            if c.domain in cleanup_domains:
                try:
                    self.s.cookies.delete(c.name, domain=c.domain, path=c.path)
                    cleaned += 1
                except Exception:
                    pass
        return cleaned

    def _safe_cookie_list(self, domain_filter: str | None = None) -> list[tuple[str, str, str, str]]:
        result = []
        for c in self.s.cookies.jar:
            if domain_filter and domain_filter not in (c.domain or ""):
                continue
            result.append((c.name, c.value, c.domain, c.path))
        return result

    # ── Helpers ──

    def _gen_signin_fwcim(self) -> str:
        loc_url = f"{SIGNIN}/platform/{DIR_ID}/signup?workflowStateHandle={self.wsh or ''}"
        ubid = self._aws_ubid_main or self._platform_ubid
        return gen_fwcim(loc_url, ubid, self._canvas_hash)

    def _exec(self, step_id: str, inputs: list | None = None, prefix: str = "",
              action_id: str | None = None, extra_fields: dict | None = None) -> dict | None:
        url = f"{SIGNIN}/platform/{DIR_ID}{prefix}/api/execute"
        body = {"stepId": step_id, "workflowStateHandle": self.wsh or "",
                "inputs": inputs or [], "requestId": _uuid()}
        if action_id:
            body["actionId"] = action_id
        if extra_fields:
            body.update(extra_fields)
        h = {**UA, "accept": "application/json", "content-type": "application/json",
             "origin": SIGNIN, "referer": f"{SIGNIN}/platform/{DIR_ID}/login"}
        self.log(f"  POST {url}")
        self.log(f"  stepId='{step_id}' actionId={action_id} wsh={str(self.wsh)[:40]}...")
        r = self.s.post(url, headers=h, json=body)
        self.log(f"  Status: {r.status_code}")
        self._capture_cookies(r)
        if r.status_code != 200:
            self.log(f"  ❌ {r.status_code}: {r.text[:500]}")
            return None
        try:
            d = r.json()
        except Exception:
            self.log(f"  ❌ Not JSON: {r.text[:300]}")
            return None
        if d.get("workflowStateHandle"):
            self.wsh = d["workflowStateHandle"]
        if d.get("stepId") is not None:
            self.sid = d["stepId"]
        self.log(f"  → sid={self.sid} wsh={str(self.wsh)[:40]}...")
        self.log(f"  Resp: {json.dumps(d, ensure_ascii=False)[:400]}")
        return d

    def _profile_headers(self) -> dict:
        return {**UA, "accept": "*/*", "accept-language": "en-US,en;q=0.9",
                "content-type": "application/json;charset=UTF-8",
                "origin": PROFILE,
                "referer": f"{PROFILE}/?workflowID={self._profile_wf_id or ''}",
                "priority": "u=1, i",
                "sec-fetch-site": "same-origin", "sec-fetch-mode": "cors",
                "sec-fetch-dest": "empty"}

    def _profile_post(self, endpoint: str, payload: dict) -> dict | None:
        url = f"{PROFILE}{endpoint}"
        h = self._profile_headers()
        self.log(f"  POST {url}")
        r = self.s.post(url, headers=h, json=payload)
        self.log(f"  Status: {r.status_code}")
        self._capture_cookies(r)
        if r.status_code not in (200, 201):
            self.log(f"  ❌ {r.status_code}: {r.text[:500]}")
            return None
        try:
            d = r.json()
            self.log(f"  Resp: {json.dumps(d, ensure_ascii=False)[:400]}")
            return d
        except Exception:
            return {}

    def _setup_profile_cookies(self) -> None:
        self.s.cookies.set("i18next", "en-US", domain="profile.aws.amazon.com", path="/")
        if self._aws_ubid_main:
            self.s.cookies.set("aws-ubid-main", self._aws_ubid_main, domain=".amazon.com", path="/")
        awsccc = json.dumps({"e": 1, "p": 1, "f": 1, "a": 1, "i": _uuid(), "v": "1"},
                            separators=(",", ":"))
        self.s.cookies.set("awsccc", base64.b64encode(awsccc.encode()).decode(),
                           domain="profile.aws.amazon.com", path="/")
        self.s.cookies.set("aws-user-profile-ubid", self._profile_ubid,
                           domain="profile.aws.amazon.com", path="/")

    def _browser_data(self, page_name: str | None = None, event_type: str = "PageLoad") -> dict:
        elapsed = 0
        if self._profile_load_ts:
            elapsed = int((time.time() - self._profile_load_ts) * 1000)
        loc_url = f"{SIGNIN}/platform/{DIR_ID}/login?workflowStateHandle={self.wsh or ''}"
        ubid_main = self._aws_ubid_main or _ubid()
        fp = gen_fwcim(loc_url, ubid_main, self._canvas_hash)
        bd = {"attributes": {
            "fingerprint": fp,
            "eventTimestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
            "timeSpentOnPage": str(max(elapsed, random.randint(2000, 5000))),
            "eventType": event_type,
            "ubid": self._profile_ubid,
        }, "cookies": {}}
        if page_name:
            bd["attributes"]["pageName"] = page_name
        if self._tes_visitor_id:
            bd["attributes"]["visitorId"] = self._tes_visitor_id
        return bd

    # ═══ Step 1: Kiro InitiateLogin ═══

    def step1_kiro_init(self) -> str | None:
        self.log("Step 1: Kiro InitiateLogin...")
        body = cbor2.dumps({
            "idp": "BuilderId",
            "redirectUri": f"{KIRO}/signin/oauth",
            "state": self.state,
            "codeChallenge": self.cc,
            "codeChallengeMethod": "S256",
        })
        h = {**UA, "accept": "application/cbor", "content-type": "application/cbor",
             "smithy-protocol": "rpc-v2-cbor", "origin": KIRO,
             "referer": f"{KIRO}/signin", "x-kiro-visitorid": self.vid,
             "amz-sdk-invocation-id": _uuid(), "amz-sdk-request": "attempt=1; max=1",
             "x-amz-user-agent": "aws-sdk-js/1.0.0 ua/2.1 os/macOS lang/js md/browser#Chromium_131 m/N,M,E"}
        r = self.s.post(f"{KIRO}/service/KiroWebPortalService/operation/InitiateLogin",
                        headers=h, data=body, cookies={"kiro-visitor-id": self.vid})
        if r.status_code != 200:
            self.log(f"  ❌ {r.status_code}")
            return None
        try:
            d = cbor2.loads(r.content)
        except Exception:
            d = r.json()
        redir = d.get("redirectUrl")
        if not redir:
            self.log(f"  ❌ No redirectUrl: {d}")
            return None
        self.log(f"  ✅ {redir[:100]}...")
        return redir

    # ═══ Step 2: Redirect chain → wsh ═══

    def step2_get_wsh(self, redir_url: str) -> bool:
        self.log("Step 2: Redirect chain...")
        p0 = urlparse(redir_url)
        qs0 = parse_qs(p0.query)
        cb = qs0.get("callback_url", [None])[0]
        self._callback_url = cb
        self.log(f"  callback_url={cb}")
        r = self.s.get(redir_url, headers={**UA, "accept": "text/html"}, allow_redirects=True)
        view_url = str(r.url)
        self.log(f"  2a status={r.status_code}, history={len(r.history)}, url={view_url[:120]}")
        m = re.search(r"workflowStateHandle=([^&#]+)", view_url)
        if m:
            self.wsh = m.group(1)
            self._login_wsh = self.wsh
            self.log(f"  ✅ wsh={self.wsh}")
            self._capture_cookies(r)
        else:
            self.log(f"  ❌ No workflowStateHandle in URL")
            return False
        self._orchestrator_id = None
        self.log("  2b Get CSRF token from portal.sso...")
        try:
            vr = (f"https://view.awsapps.com/start/#/"
                  f"?callback_url={url_quote(cb or '')}&orchestrator_id=placeholder")
            pu = (f"{PORTAL_SSO}/login?directory_id=view&redirect_url={url_quote(vr)}")
            r2 = self.s.get(pu, headers={**UA, "accept": "*/*",
                            "origin": "https://view.awsapps.com",
                            "referer": "https://view.awsapps.com/",
                            "sec-fetch-site": "cross-site", "sec-fetch-mode": "cors",
                            "sec-fetch-dest": "empty"}, allow_redirects=False)
            self.log(f"  Status: {r2.status_code}")
            d = r2.json()
            csrf = d.get("csrfToken")
            if csrf:
                self._portal_csrf_token = str(csrf)
                self.log(f"  ★ portal csrfToken={self._portal_csrf_token}")
        except Exception as e:
            self.log(f"  ⚠️ portal.sso: {e}")
        self._setup_signin_js_cookies()
        return True

    # ═══ Step 3: signin.aws → SIGNUP ═══

    def step3_signin_flow(self, email: str) -> dict | None:
        self.log("Step 3: signin.aws workflow...")
        fp_i = {"input_type": "FingerPrintRequestInput", "fingerPrint": self._gen_signin_fwcim()}
        usr_i = {"input_type": "UserRequestInput", "username": email}
        self.log("  3a: init (stepId='')...")
        if not self._exec("", inputs=[fp_i]):
            return None
        self.log("  3b: start → get-identity-user...")
        if not self._exec("start", inputs=[fp_i]):
            return None
        self.log("  3c: SIGNUP...")
        r = self._exec("get-identity-user", inputs=[usr_i, fp_i], action_id="SIGNUP")
        if not r:
            return None
        redir = r.get("redirect", {}).get("url")
        if redir:
            self.log(f"  ✅ signup redirect: {redir[:100]}...")
            m = re.search(r"workflowStateHandle=([^&#]+)", redir)
            if m:
                self.wsh = m.group(1)
        return r

    # ═══ Step 4: signup → profile.aws redirect ═══

    def step4_signup_flow(self, email: str) -> dict | None:
        self.log("Step 4: signup workflow...")
        fp_i = {"input_type": "FingerPrintRequestInput", "fingerPrint": self._gen_signin_fwcim()}
        usr_i = {"input_type": "UserRequestInput", "username": email}
        self.log("  4a: signup init...")
        if not self._exec("", inputs=[usr_i, fp_i], prefix="/signup"):
            return None
        self._update_directory_csrf_with_signup()
        self.log("  4b: signup start...")
        r = self._exec("start", inputs=[usr_i, fp_i], prefix="/signup")
        if not r:
            return None
        redir = r.get("redirect", {}).get("url", "")
        if "profile.aws" in redir:
            self.log(f"  ✅ profile redirect: {redir[:100]}...")
            m = re.search(r"workflowID=([^&#]+)", redir)
            if m:
                self._profile_wf_id = m.group(1)
                self.log(f"  workflowID: {self._profile_wf_id}")
        self._signup_wsh = self.wsh
        return r

    # ═══ Step 5: TES token ═══

    def step5_get_tes_token(self) -> str | None:
        self.log("Step 5: Get TES token...")
        self.log("  Loading signin.aws resources...")
        for path in ["/assets/js/app.js"]:
            r = self.s.get(f"{SIGNIN}{path}", headers={**UA, "accept": "*/*",
                           "referer": f"{SIGNIN}/platform/{DIR_ID}/login"})
            self._capture_cookies(r)
        self.s.post(f"{SIGNIN}/metrics/fingerprint",
                    headers={**UA, "accept": "*/*", "content-type": "application/json",
                             "origin": SIGNIN, "referer": f"{SIGNIN}/platform/{DIR_ID}/login"},
                    json={"fingerprint": self._gen_signin_fwcim()})
        r = self.s.post("https://vs.aws.amazon.com/token",
                        headers={**UA, "accept": "*/*", "content-type": "application/json",
                                 "origin": SIGNIN, "referer": f"{SIGNIN}/",
                                 "sec-fetch-site": "cross-site", "sec-fetch-mode": "cors",
                                 "sec-fetch-dest": "empty"}, json={})
        self._capture_cookies(r)
        self.log(f"  Status: {r.status_code}")
        if r.status_code == 200:
            d = r.json()
            token = d.get("token", "")
            self.log(f"  ✅ awsd2c-token: {token[:60]}...")
            self._awsd2c_token = token
            try:
                parts = token.split(".")
                pb = parts[1] + "=" * (4 - len(parts[1]) % 4)
                jp = json.loads(base64.urlsafe_b64decode(pb))
                self._tes_visitor_id = jp.get("vid")
                self.log(f"  ✅ visitorId: {self._tes_visitor_id}")
            except Exception:
                pass
            for domain in [".aws.amazon.com"]:
                self.s.cookies.set("awsd2c-token", token, domain=domain, path="/")
                self.s.cookies.set("awsd2c-token-c", token, domain=domain, path="/")
            self.s.cookies.set("awsd2c-token-c", token, domain="us-east-1.signin.aws", path="/")
            return token
        self.log(f"  ❌ {r.status_code}: {r.text[:300]}")
        return None

    # ═══ Step 6: profile.aws page load + /api/start ═══

    def step6_profile_load(self) -> dict | None:
        self.log("Step 6: profile.aws page loading...")
        if not self._profile_wf_id:
            self.log("  ❌ No workflowID")
            return None
        self._setup_profile_cookies()
        self.log("  6a: GET profile page...")
        r = self.s.get(f"{PROFILE}?workflowID={self._profile_wf_id}",
                       headers={**UA, "accept": "text/html", "referer": f"{SIGNIN}/"},
                       allow_redirects=True)
        self._capture_cookies(r)
        self._profile_load_ts = time.time()
        self.log(f"  Page status: {r.status_code}")
        for res in ["/dist/main/app_3d2790dc68bef818e50a.min.js",
                     "/dist/main/app_f95ebcaf22d26fd182da.min.css"]:
            self.s.get(f"{PROFILE}{res}", headers={**UA, "accept": "*/*",
                       "referer": f"{PROFILE}/?workflowID={self._profile_wf_id}"})
        time.sleep(0.3)
        self.log("  6b: POST /api/get-config...")
        self._profile_post("/api/get-config", {})
        self.log("  6c: POST /api/get-app-context...")
        self.s.post(f"{PROFILE}/api/get-app-context",
                    headers=self._profile_headers(),
                    json={"workflowID": self._profile_wf_id})
        time.sleep(0.5)
        self.log("  6d: POST /api/start...")
        payload = {"workflowID": self._profile_wf_id, "browserData": self._browser_data()}
        r = self._profile_post("/api/start", payload)
        if r and r.get("workflowState"):
            self._profile_wf_state = r["workflowState"]
            self.log(f"  ✅ workflowState: {self._profile_wf_state}")
        return r

    # ═══ Step 7: send-otp ═══

    def step7_send_otp(self, email: str) -> dict | None:
        self.log(f"Step 7: send-otp to {email}...")
        time.sleep(random.uniform(2.0, 4.0))
        payload = {"workflowState": self._profile_wf_state, "email": email,
                   "browserData": self._browser_data(page_name="EMAIL_COLLECTION",
                                                     event_type="PageSubmit")}
        return self._profile_post("/api/send-otp", payload)

    # ═══ Step 8: create-identity ═══

    def step8_create_identity(self, otp: str, email: str, full_name: str) -> dict | None:
        self.log("Step 8: create-identity...")
        time.sleep(random.uniform(1.0, 3.0))
        payload = {
            "workflowState": self._profile_wf_state,
            "userData": {"email": email, "fullName": full_name},
            "otpCode": otp,
            "browserData": self._browser_data(page_name="EMAIL_VERIFICATION",
                                              event_type="EmailVerification"),
        }
        r = self._profile_post("/api/create-identity", payload)
        if not r:
            return None
        reg_code = r.get("registrationCode")
        sign_in_state = r.get("signInState")
        if not reg_code or not sign_in_state:
            self.log("  ❌ Missing registrationCode or signInState")
            return None
        self.log(f"  ✅ registrationCode: {reg_code[:40]}...")
        try:
            padded = sign_in_state + "=" * (4 - len(sign_in_state) % 4)
            decoded = json.loads(base64.b64decode(padded))
            self.log(f"  signInState decoded: {decoded}")
        except Exception:
            pass
        return r

    # ═══ Step 9: signup registration ═══

    def step9_signup_registration(self, reg_code: str, sign_in_state: str) -> dict | None:
        self.log("Step 9: signup with registrationCode...")
        self._setup_signin_js_cookies()
        try:
            self.s.cookies.delete("awsccc", domain="us-east-1.signin.aws")
        except Exception:
            pass
        awsccc = json.dumps({"e": 1, "p": 1, "f": 1, "a": 1, "i": _uuid(), "v": "1"},
                            separators=(",", ":"))
        self.s.cookies.set("awsccc", base64.b64encode(awsccc.encode()).decode(),
                           domain="us-east-1.signin.aws", path="/")

        signup_url = (f"{SIGNIN}/platform/{DIR_ID}/signup"
                      f"?registrationCode={reg_code}&state={sign_in_state}")
        self.log(f"  9a: GET {signup_url[:100]}...")
        r = self.s.get(signup_url, headers={**UA, "accept": "text/html",
                       "referer": f"{PROFILE}/"}, allow_redirects=True)
        self._capture_cookies(r)
        self.log(f"  Status: {r.status_code}")

        self.s.get(f"{SIGNIN}/assets/js/app.js",
                   headers={**UA, "accept": "*/*", "referer": signup_url})
        self.s.get(f"{SIGNIN}/assets/css/app.css",
                   headers={**UA, "accept": "text/css", "referer": signup_url})
        self.s.get(f"{SIGNIN}/platform/config?directoryId=",
                   headers={**UA, "accept": "*/*", "referer": signup_url})
        time.sleep(0.5)

        req_id = _uuid()
        fwcim = self._gen_signin_fwcim()
        fp_i = {"input_type": "FingerPrintRequestInput", "fingerPrint": fwcim}
        reg_i = {"input_type": "UserRegistrationRequestInput",
                 "registrationCode": reg_code, "state": sign_in_state}
        self.log("  9b: POST signup/api/execute (registrationCode)...")
        url = f"{SIGNIN}/platform/{DIR_ID}/signup/api/execute"
        body = {"stepId": "", "state": sign_in_state, "inputs": [reg_i, fp_i], "requestId": req_id}
        h = {**UA, "accept": "application/json, text/plain, */*",
             "content-type": "application/json; charset=UTF-8",
             "origin": SIGNIN, "x-amzn-requestid": req_id,
             "x-amz-date": time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime()),
             "referer": signup_url, "sec-fetch-site": "same-origin",
             "sec-fetch-mode": "cors", "sec-fetch-dest": "empty",
             "sec-gpc": "1", "priority": "u=1, i"}

        self.log("  Sent cookies (signin.aws):")
        for name, val, dom, path in self._safe_cookie_list("signin.aws"):
            self.log(f"    {name}={str(val)[:60]}... (domain={dom}, path={path})")

        r = self.s.post(url, headers=h, json=body)
        self.log(f"  Status: {r.status_code}")
        self._capture_cookies(r)
        if r.status_code != 200:
            self.log(f"  ❌ {r.status_code}: {r.text[:500]}")
            return None
        d = r.json()
        self.log(f"  → sid={d.get('stepId')} wsh={d.get('workflowStateHandle', '')[:40]}")
        self.log(f"  Resp: {json.dumps(d, ensure_ascii=False)[:400]}")
        if d.get("stepId") != "get-new-password-for-password-creation":
            self.log(f"  ❌ Expected get-new-password, actual {d.get('stepId')}")
            return None

        self.log("  ✅ Entering password setup step")
        self._signup_reg_url = signup_url
        return d

    # ═══ Step 10: Set password (JWE) ═══

    def step10_set_password(self, pwd: str, email: str, step9_resp: dict) -> dict | None:
        self.log("Step 10: Set password (JWE encryption)...")
        wsh = step9_resp.get("workflowStateHandle", "")
        enc_ctx = (step9_resp.get("workflowResponseData", {})
                   .get("encryptionContextResponse", {}))
        pub_key = enc_ctx.get("publicKey")
        if not pub_key:
            self.log("  ❌ No public key, cannot encrypt password")
            return None
        self.log(f"  Public key kid: {pub_key.get('kid')}")

        for c in list(self.s.cookies.jar):
            if c.domain and c.domain.startswith(".") and "signin.aws" in c.domain:
                try:
                    self.s.cookies.delete(c.name, domain=c.domain, path=c.path)
                except Exception:
                    pass

        fwcim = self._gen_signin_fwcim()
        fp_i = {"input_type": "FingerPrintRequestInput", "fingerPrint": fwcim}
        evt_load = {
            "inputs": [
                {"input_type": "UserEventRequestInput",
                 "directoryId": DIR_ID, "userName": email,
                 "userEvents": [{"input_type": "UserEvent",
                                 "eventType": "PAGE_LOAD",
                                 "pageName": "CREDENTIAL_COLLECTION"}]},
                fp_i,
            ],
            "requestId": _uuid(),
        }
        referer = getattr(self, '_signup_reg_url', f"{SIGNIN}/platform/{DIR_ID}/signup")
        se_h = {**UA, "accept": "application/json, text/plain, */*",
                "content-type": "application/json; charset=UTF-8",
                "origin": SIGNIN, "x-amzn-requestid": evt_load["requestId"],
                "x-amz-date": time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime()),
                "referer": referer, "sec-fetch-site": "same-origin",
                "sec-fetch-mode": "cors", "sec-fetch-dest": "empty"}
        self.log("  10a: send-event (PAGE_LOAD CREDENTIAL_COLLECTION)...")
        self.s.post(f"{SIGNIN}/platform/user-event/send-event", headers=se_h, json=evt_load)

        fwcim2 = self._gen_signin_fwcim()
        self.s.post(f"{SIGNIN}/metrics/fingerprint",
                    headers={**UA, "accept": "*/*",
                             "content-type": "application/x-www-form-urlencoded",
                             "origin": SIGNIN, "referer": referer},
                    data=f"name=IsFingerprintGenerated:Success&value={fwcim2}")

        time.sleep(random.uniform(1.0, 3.0))

        jwe_password = encrypt_password_jwe(pwd, pub_key)
        self.log(f"  ✅ JWE encryption completed, length={len(jwe_password)}")

        req_id = _uuid()
        fwcim3 = self._gen_signin_fwcim()
        fp_i2 = {"input_type": "FingerPrintRequestInput", "fingerPrint": fwcim3}
        pwd_i = {"input_type": "PasswordRequestInput", "password": jwe_password,
                 "successfullyEncrypted": "SUCCESSFUL", "errorLog": None}
        usr_i = {"input_type": "UserRequestInput", "username": email}
        evt_i = {"input_type": "UserEventRequestInput", "directoryId": DIR_ID,
                 "userName": email,
                 "userEvents": [{"input_type": "UserEvent", "eventType": "PAGE_SUBMIT",
                                 "pageName": "CREDENTIAL_COLLECTION",
                                 "timeSpentOnPage": random.randint(8000, 25000)}]}
        url = f"{SIGNIN}/platform/{DIR_ID}/signup/api/execute"
        body = {"stepId": "get-new-password-for-password-creation",
                "workflowStateHandle": wsh, "actionId": "SUBMIT",
                "inputs": [pwd_i, evt_i, usr_i, fp_i2],
                "visitorId": self._tes_visitor_id or "", "requestId": req_id}
        h = {**UA, "accept": "application/json, text/plain, */*",
             "content-type": "application/json; charset=UTF-8",
             "origin": SIGNIN, "x-amzn-requestid": req_id,
             "x-amz-date": time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime()),
             "referer": referer, "sec-fetch-site": "same-origin",
             "sec-fetch-mode": "cors", "sec-fetch-dest": "empty",
             "sec-gpc": "1", "priority": "u=1, i"}



        cleaned = self._clean_non_bare_domain_cookies()
        if cleaned:
            self.log(f"  ★ Cleaned {cleaned} non-bare-domain cookies")

        self.log("  10b cookies:")
        for name, val, dom, path in self._safe_cookie_list("signin.aws"):
            self.log(f"    {name}={str(val)[:50]}... (d={dom} p={path})")

        self.log(f"  10b: POST {url}")
        r = self.s.post(url, headers=h, json=body)
        self.log(f"  Status: {r.status_code}")
        self._capture_cookies(r)
        if r.status_code != 200:
            self.log(f"  ❌ {r.status_code}: {r.text[:500]}")
            return None
        d = r.json()
        self.log(f"  → sid={d.get('stepId')}")
        self.log(f"  Resp: {json.dumps(d, ensure_ascii=False)[:400]}")
        if d.get("stepId") != "end-of-user-registration-success":
            self.log(f"  ❌ Expected end-of-user-registration-success")
            return None
        redir_url = d.get("redirect", {}).get("url", "")
        if redir_url:
            m_wrh = re.search(r"workflowResultHandle=([^&#]+)", redir_url)
            if m_wrh:
                self._workflow_result_handle = m_wrh.group(1)
                self.log(f"  ★ workflowResultHandle={self._workflow_result_handle}")
        self.log("  ✅ Password set successfully, registration complete!")
        return d

    # ═══ Step 11: Final login ═══

    def step11_final_login(self, email: str, step10_resp: dict) -> dict | None:
        self.log("Step 11: Final login...")
        redir = step10_resp.get("redirect", {}).get("url", "")
        if not redir:
            self.log("  ❌ No redirect URL")
            return None
        self.log(f"  redirect: {redir[:120]}...")
        p = urlparse(redir)
        qs = parse_qs(p.query)
        login_wsh = qs.get("workflowStateHandle", [None])[0]
        state = qs.get("state", [None])[0]
        wf_result = qs.get("workflowResultHandle", [None])[0]
        if not login_wsh or not state or not wf_result:
            self.log("  ❌ redirect parameters incomplete")
            return None
        fwcim = self._gen_signin_fwcim()
        fp_i = {"input_type": "FingerPrintRequestInput", "fingerPrint": fwcim}
        usr_i = {"input_type": "UserRequestInput", "username": email}
        url = f"{SIGNIN}/platform/{DIR_ID}/api/execute"
        body = {"stepId": "", "workflowStateHandle": login_wsh,
                "workflowResultHandle": wf_result, "state": state,
                "inputs": [usr_i, fp_i],
                "visitorId": self._tes_visitor_id or "", "requestId": _uuid()}
        h = {**UA, "accept": "application/json", "content-type": "application/json",
             "origin": SIGNIN, "referer": f"{SIGNIN}/platform/{DIR_ID}/login"}
        self.log(f"  POST {url}")
        r = self.s.post(url, headers=h, json=body)
        self.log(f"  Status: {r.status_code}")
        self._capture_cookies(r)
        if r.status_code != 200:
            self.log(f"  ❌ {r.status_code}: {r.text[:500]}")
            return None
        d = r.json()
        self.log(f"  → sid={d.get('stepId')}")
        if d.get("stepId") == "end-of-workflow-success":
            self.log("  ✅ Login successful! workflow complete!")
            redir11 = d.get("redirect", {}).get("url", "")
            if redir11:
                self._step12_redirect_url = redir11
                self.log(f"  ★ step12 redirect={redir11[:120]}...")
                p11 = urlparse(redir11)
                qs11 = parse_qs(p11.query)
                s11 = qs11.get("state", [None])[0]
                if s11:
                    self._step11_state = s11
                    self.log(f"  ★ step11 state={s11[:60]}...")
                wrh11 = qs11.get("workflowResultHandle", [None])[0]
                if wrh11:
                    self._workflow_result_handle = wrh11
                    self.log(f"  ★ step11 workflowResultHandle={wrh11} (overrides step10 value)")
        else:
            self.log(f"  ⚠️ stepId={d.get('stepId')}, may need additional steps")
        return d

    # ═══ Step 12: OIDC Auth Code Flow → accessToken + sessionToken ═══

    def step12_get_tokens(self) -> dict | None:
        self.log("Step 12: OIDC Auth Code Flow → Get tokens...")

        redir_url = self._step12_redirect_url
        if not redir_url:
            self.log("  ❌ Missing step12 redirect URL (step 11)")
            return None

        self.log("  12a: Follow redirect chain to app.kiro.dev (get auth code)...")
        self.log(f"  GET {redir_url[:150]}...")
        r = self.s.get(redir_url, headers={**UA, "accept": "text/html,application/xhtml+xml,*/*",
                       "referer": "https://us-east-1.signin.aws/"}, allow_redirects=True)
        self.log(f"  Status: {r.status_code}, history={len(r.history)}, final URL: {str(r.url)[:180]}")
        final_url = str(r.url)

        p_loc = urlparse(final_url)
        qs_loc = parse_qs(p_loc.query)
        fqs_extra = parse_qs(p_loc.fragment.lstrip("#/?")) if p_loc.fragment else {}
        auth_code = qs_loc.get("code", [None])[0] or fqs_extra.get("code", [None])[0]
        redirect_state = qs_loc.get("state", [None])[0] or fqs_extra.get("state", [None])[0]
        if not auth_code:
            self.log(f"  ❌ No code parameter in final URL: {final_url[:200]}")
            self._capture_cookies(r)
            return None
        if not redirect_state:
            self.log("  ⚠️ No state parameter, fallback to self.state")
            redirect_state = self.state
        self.log(f"  ✅ auth_code={auth_code[:60]}...")
        self.log(f"  ✅ redirect_state={redirect_state[:60]}...")

        self.log("  12e: POST ExchangeToken (CBOR)...")
        exchange_body = cbor2.dumps({"code": auth_code, "codeVerifier": self.cv,
                                      "idp": "BuilderId",
                                      "redirectUri": f"{KIRO}/signin/oauth",
                                      "state": redirect_state})
        exchange_h = {**UA, "accept": "application/cbor",
                      "content-type": "application/cbor",
                      "smithy-protocol": "rpc-v2-cbor", "origin": KIRO,
                      "referer": f"{KIRO}/signin", "x-kiro-visitorid": self.vid,
                      "amz-sdk-invocation-id": _uuid(), "amz-sdk-request": "attempt=1; max=1",
                      "x-amz-user-agent": "aws-sdk-js/1.0.0 ua/2.1 "
                                          "os/macOS lang/js md/browser#Chromium_131 m/N,M,E"}
        r = self.s.post(f"{KIRO}/service/KiroWebPortalService/operation/ExchangeToken",
                        headers=exchange_h, data=exchange_body,
                        cookies={"kiro-visitor-id": self.vid})
        self.log(f"  Status: {r.status_code}")
        if r.status_code != 200:
            self.log(f"  ❌ ExchangeToken failed: {r.status_code}")
            try:
                self.log(f"  {r.text[:500]}")
            except Exception:
                self.log(f"  (binary response, len={len(r.content)})")
            return None
        try:
            resp_data = cbor2.loads(r.content)
        except Exception as e:
            self.log(f"  ❌ CBOR parsing failed: {e}")
            return None
        access_token = resp_data.get("accessToken", "")
        kiro_csrf = resp_data.get("csrfToken", "")
        expires_in = resp_data.get("expiresIn", 0)
        if not access_token:
            self.log(f"  ❌ No accessToken: {resp_data}")
            return None
        self.log(f"  ✅ accessToken={access_token[:60]}...")
        self.log(f"  ✅ csrfToken={kiro_csrf[:30]}...")
        self.log(f"  expiresIn={expires_in}")

        # Extract SessionToken, UserId, Idp from the curl session cookie jar
        session_token = ""
        user_id = ""
        idp = ""
        for c in self.s.cookies.jar:
            if c.name == "SessionToken" and "kiro.dev" in (c.domain or ""):
                session_token = c.value
            elif c.name == "UserId" and "kiro.dev" in (c.domain or ""):
                user_id = c.value
            elif c.name == "Idp" and "kiro.dev" in (c.domain or ""):
                idp = c.value
        if session_token:
            self.log(f"  ✅ sessionToken={session_token[:50]}...")
        if user_id:
            self.log(f"  ✅ userId={user_id[:50]}...")

        return {
            "accessToken": access_token,
            "csrfToken": kiro_csrf,
            "expiresIn": expires_in,
            "sessionToken": session_token,
            "userId": user_id,
            "idp": idp or "BuilderId",
        }

    # ═══ Step 12f-12i: OIDC Device Auth → refreshToken ═══

    def _extract_ssosession_token(self) -> str:
        """Extract the raw SSO session token (stc) from aws-usi-authn cookie."""
        for c in self.s.cookies.jar:
            if c.name == "aws-usi-authn":
                try:
                    raw_value = url_unquote(c.value)
                    padded = raw_value + "=" * (4 - len(raw_value) % 4) if len(raw_value) % 4 else raw_value
                    decoded = base64.b64decode(padded).decode("utf-8")
                    parsed = json.loads(decoded)
                    stc = parsed.get("stc", "")
                    if stc:
                        return stc
                except Exception:
                    pass
        return ""

    def step12f_device_auth(self, bearer_token: str) -> dict | None:
        self.log("Step 12f: OIDC Device Auth → refreshToken...")

        # Use the raw SSO session token (stc) — saved earlier in step 10,
        # or fall back to live cookie lookup.
        sso_session = self._ssosession_token or self._extract_ssosession_token()
        if sso_session:
            self.log(f"  ✅ SSO session token: {sso_session[:50]}...")

        self.log("  12f: POST oidc/client/register...")
        reg_h = {"content-type": "application/json",
                 "user-agent": "aws-sdk-rust/1.3.9 os/windows lang/rust/1.87.0",
                 "x-amz-user-agent": "aws-sdk-rust/1.3.9 ua/2.1 "
                                     "api/ssooidc/1.88.0 os/windows lang/rust/1.87.0 "
                                     "m/E app/AmazonQ-For-CLI",
                 "amz-sdk-request": "attempt=1; max=3",
                 "amz-sdk-invocation-id": _uuid()}
        reg_body = {"clientName": "Amazon Q Developer for command line",
                    "clientType": "public",
                    "scopes": ["codewhisperer:completions", "codewhisperer:analysis",
                               "codewhisperer:conversations"],
                    "grantTypes": ["urn:ietf:params:oauth:grant-type:device_code",
                                   "refresh_token"],
                    "issuerUrl": "https://identitycenter.amazonaws.com/ssoins-722374e5d5e7e3e0"}
        r = self.s.post(f"{OIDC}/client/register", headers=reg_h, json=reg_body)
        self.log(f"  Status: {r.status_code}")
        if r.status_code != 200:
            self.log(f"  ❌ client/register failed: {r.text[:300]}")
            return None
        reg_resp = r.json()
        client_id = reg_resp.get("clientId", "")
        client_secret = reg_resp.get("clientSecret", "")
        if not client_id or not client_secret:
            self.log("  ❌ No clientId/clientSecret")
            return None
        self.log(f"  ✅ clientId={client_id[:40]}...")

        self.log("  12g: POST oidc/device_authorization...")
        da_h = {**reg_h, "amz-sdk-invocation-id": _uuid()}
        da_body = {"clientId": client_id, "clientSecret": client_secret,
                   "startUrl": "https://view.awsapps.com/start"}
        r = self.s.post(f"{OIDC}/device_authorization", headers=da_h, json=da_body)
        self.log(f"  Status: {r.status_code}")
        if r.status_code != 200:
            self.log(f"  ❌ device_authorization failed: {r.text[:300]}")
            return None
        da_resp = r.json()
        device_code = da_resp.get("deviceCode", "")
        user_code = da_resp.get("userCode", "")
        interval = da_resp.get("interval", 1)
        if not device_code or not user_code:
            self.log("  ❌ No deviceCode/userCode")
            return None
        self.log(f"  ✅ userCode={user_code}")

        self.log("  12h: SSO portal session + device authorization confirmation...")
        oidc_h = {**UA, "accept": "application/json, text/plain, */*",
                  "content-type": "application/json",
                  "origin": "https://view.awsapps.com",
                  "referer": "https://view.awsapps.com/",
                  "sec-fetch-site": "cross-site", "sec-fetch-mode": "cors",
                  "sec-fetch-dest": "empty"}

        # Step 12h-1: Create SSO portal session FIRST
        self.log("  12h-1: POST portal.sso/session/device...")
        r = self.s.post(f"{PORTAL_SSO}/session/device",
                        headers={**UA, "accept": "application/json, text/plain, */*",
                                 "content-type": "application/json",
                                 "authorization": f"Bearer {bearer_token}",
                                 "origin": "https://view.awsapps.com",
                                 "referer": "https://view.awsapps.com/",
                                 "sec-fetch-site": "cross-site", "sec-fetch-mode": "cors"},
                        json={})
        self.log(f"  Status: {r.status_code} {r.text[:500]}")
        if r.status_code != 200:
            self.log("  ⚠️ portal.sso/session/device failed, skipping device auth")
            return None
        portal_session = r.json()
        device_token = portal_session.get("token", bearer_token)
        self.log(f"  ✅ device_token={device_token[:60]}...")

        # Step 12h-2: Accept user code with the portal session token
        self.log(f"  12h-2: POST accept_user_code (userCode={user_code})...")
        # Try portal session token first, fallback to stc or bearer_token
        user_session_id = device_token or sso_session or bearer_token
        r = self.s.post(f"{OIDC}/device_authorization/accept_user_code",
                        headers=oidc_h,
                        json={"userCode": user_code, "userSessionId": user_session_id})
        self.log(f"  Status: {r.status_code} {r.text[:300]}")
        if r.status_code != 200:
            self.log("  ⚠️ accept_user_code failed, skipping rest of device auth")
            return None
        accept_resp = r.json()
        device_context = accept_resp.get("deviceContext", {})
        dc_id = device_context.get("deviceContextId", "")
        dc_client_id = device_context.get("clientId", client_id)
        dc_client_type = device_context.get("clientType", "public")
        self.log(f"  ✅ deviceContextId={dc_id[:60]}...")

        self.log("  12h-3: POST consent_details...")
        r = self.s.post(f"{OIDC}/consent_details", headers=oidc_h,
                        json={"deviceContextId": dc_id, "clientId": dc_client_id,
                              "clientType": dc_client_type, "userSessionId": device_token})
        self.log(f"  Status: {r.status_code} {r.text[:300]}")

        self.log("  12h-4: POST associate_token...")
        r = self.s.post(f"{OIDC}/device_authorization/associate_token", headers=oidc_h,
                        json={"deviceContext": {"deviceContextId": dc_id,
                                                "clientId": dc_client_id,
                                                "clientType": dc_client_type},
                              "userSessionId": device_token})
        self.log(f"  Status: {r.status_code} {r.text[:300]}")
        if r.status_code not in (200, 204):
            self.log("  ❌ associate_token failed")
            return None
        self.log("  ✅ associate_token completed")

        self.log("  12i: POST oidc/token (polling for refreshToken)...")
        token_h = {**reg_h, "amz-sdk-invocation-id": _uuid()}
        token_body = {"clientId": client_id, "clientSecret": client_secret,
                      "deviceCode": device_code,
                      "grantType": "urn:ietf:params:oauth:grant-type:device_code"}
        poll_start = time.time()
        poll_timeout = 60
        poll_interval = max(interval, 1)
        oidc_token = None
        while time.time() - poll_start < poll_timeout:
            r = self.s.post(f"{OIDC}/token", headers=token_h, json=token_body)
            if r.status_code == 200:
                oidc_token = r.json()
                break
            try:
                err = r.json()
                err_code = err.get("error", "")
                if err_code == "authorization_pending":
                    self.log("  Polling... (authorization_pending)")
                elif err_code == "slow_down":
                    poll_interval = min(poll_interval + 1, 10)
                    self.log(f"  slow_down, interval={poll_interval}s")
                else:
                    self.log(f"  ❌ Token error: {err_code} - {err.get('error_description', '')}")
                    return None
            except Exception:
                self.log(f"  ❌ Token response exception: {r.status_code} {r.text[:200]}")
                return None
            time.sleep(poll_interval)
        if not oidc_token:
            self.log("  ❌ Token polling timeout")
            return None
        oidc_access = oidc_token.get("accessToken", "")
        refresh_token = oidc_token.get("refreshToken", "")
        self.log(f"  ✅ OIDC accessToken={oidc_access[:60]}...")
        self.log(f"  ✅ refreshToken={refresh_token[:60]}...")
        return {
            "clientId": client_id,
            "clientSecret": client_secret,
            "accessToken": oidc_access,
            "refreshToken": refresh_token,
        }

    # ═══ High-level registration ═══

    def register(self, email: str, pwd: str | None = None,
                 name: str = "Kiro User", mail_token: str | None = None,
                 otp_timeout: int = 120, otp_callback=None) -> tuple[bool, dict]:
        use_password = pwd or _pwd()
        self.log(f"  Auto-generated password: {use_password}" if not pwd
                 else f"  Using provided password: {use_password}")
        self.log(f"========== Starting registration: {email} ==========")

        redir = self.step1_kiro_init()
        if not redir:
            return False, {"error": "InitiateLogin failed"}
        if not self.step2_get_wsh(redir):
            return False, {"error": "Failed to get wsh"}
        if not self.step3_signin_flow(email):
            return False, {"error": "signin flow failed"}
        if not self.step4_signup_flow(email):
            return False, {"error": "signup flow failed"}
        if not self._profile_wf_id:
            return False, {"error": "Failed to get workflowID"}

        tes = self.step5_get_tes_token()
        if not tes:
            self.log("  ⚠️ TES token fetch failed, continuing...")

        if not self.step6_profile_load():
            return False, {"error": "profile start failed"}
        if self.step7_send_otp(email) is None:
            return False, {"error": "send OTP failed"}

        if otp_callback:
            self.log("  Auto-fetching OTP...")
            otp = otp_callback()
        elif mail_token:
            self.log("  Auto-fetching OTP...")
            otp = wait_for_otp(mail_token, timeout=otp_timeout, tag=self.tag)
        else:
            otp = input(f"[{self.tag}] Please enter OTP: ").strip()
        if not otp:
            return False, {"error": "Failed to get OTP"}

        identity = self.step8_create_identity(otp, email, name)
        if not identity:
            return False, {"error": "create-identity failed"}
        reg_code = identity["registrationCode"]
        sign_in_state = identity["signInState"]

        signup_registration = self.step9_signup_registration(reg_code, sign_in_state)
        if not signup_registration:
            return False, {"error": "signup registration failed"}
        password_state = self.step10_set_password(use_password, email, signup_registration)
        if not password_state:
            return False, {"error": "Password setup failed"}

        login_result = self.step11_final_login(email, password_state)
        if not login_result:
            self.log("  ⚠️ Final login step failed, but account may have been created successfully")

        tokens = self.step12_get_tokens()
        if not tokens:
            self.log("🎉 Registration complete! (but token fetch failed, account is usable)")
            return True, {"email": email, "password": use_password, "name": name}

        session_token = tokens.get("sessionToken", "")
        if session_token:
            device_tokens = self.step12f_device_auth(session_token)
            if device_tokens:
                self.log("🎉 Registration complete! (with accessToken + sessionToken + refreshToken)")
                return True, {
                    "email": email,
                    "password": use_password,
                    "name": name,
                    "accessToken": tokens["accessToken"],
                    "sessionToken": session_token,
                    "csrfToken": tokens.get("csrfToken", ""),
                    "userId": tokens.get("userId", ""),
                    "clientId": device_tokens["clientId"],
                    "clientSecret": device_tokens["clientSecret"],
                    "refreshToken": device_tokens["refreshToken"],
                }
            self.log("🎉 Registration complete! (with accessToken + sessionToken, but refreshToken fetch failed)")
            return True, {
                "email": email,
                "password": use_password,
                "name": name,
                "accessToken": tokens["accessToken"],
                "sessionToken": session_token,
                "csrfToken": tokens.get("csrfToken", ""),
                "userId": tokens.get("userId", ""),
            }
        self.log("🎉 Registration complete! (with accessToken, no sessionToken)")
        return True, {
            "email": email,
            "password": use_password,
            "name": name,
            "accessToken": tokens["accessToken"],
        }


# ═══════════════════════════════════════════
#  laoudo.com email API
# ═══════════════════════════════════════════

LAOUDO_API = "https://laoudo.com/api/email"
LAOUDO_ACCOUNT_ID = ""
LAOUDO_AUTH = ""
LAOUDO_EMAIL = ""


def _laoudo_headers():
    return {"accept": "application/json, text/plain, */*",
            "accept-language": "zh", "authorization": LAOUDO_AUTH,
            "referer": "https://laoudo.com/inbox", **UA}


def wait_for_otp(account_id: str | None = None, timeout: int = 120, tag: str = "") -> str | None:
    if not account_id:
        account_id = LAOUDO_ACCOUNT_ID
    prefix = f"[{tag}] " if tag else ""
    print(f"{prefix}  Waiting for verification email (max {timeout}s)...")
    h = _laoudo_headers()
    start = time.time()
    seen_ids = set()
    while time.time() - start < timeout:
        try:
            params = {"accountId": account_id, "allReceive": 0, "emailId": 0,
                      "timeSort": 0, "size": 50, "type": 0}
            r = curl_requests.get(f"{LAOUDO_API}/list", params=params, headers=h,
                                  timeout=15, impersonate="chrome131")
            if r.status_code == 200:
                data = r.json()
                mail_list = data
                if isinstance(data, dict):
                    mail_list = (data.get("data", {}).get("list")
                                 or data.get("list")
                                 or data.get("data", []))
                if not isinstance(mail_list, list):
                    mail_list = []
                for mail in mail_list:
                    mid = mail.get("id") or mail.get("emailId")
                    if not mid or mid in seen_ids:
                        continue
                    seen_ids.add(mid)
                    subject = str(mail.get("subject", "") or "")
                    content = str(mail.get("content", "") or
                                  mail.get("html", "") or
                                  mail.get("body", "") or
                                  mail.get("text", "") or "")
                    combined = subject + " " + content
                    if ("amazon" not in combined.lower() and
                        "aws" not in combined.lower() and
                        "signin" not in combined.lower() and
                        "verification" not in combined.lower()):
                        continue
                    for pat in [r"verification code[:：]\s*(\d{6})",
                                r"verification code is:?\s*(\d{6})",
                                r"Verification code:?\s*(\d{6})",
                                r">\s*(\d{6})\s*<",
                                r"\b(\d{6})\b"]:
                        m = re.search(pat, combined, re.IGNORECASE)
                        if m:
                            code = m.group(1)
                            print(f"{prefix}  ✅ Verification code: {code}")
                            return code
        except Exception as e:
            print(f"{prefix}  ⚠️ Email query exception: {e}")
        elapsed = int(time.time() - start)
        print(f"{prefix}  Waiting... ({elapsed}s/{timeout}s)")
        time.sleep(3)
    print(f"{prefix}  ❌ Verification code timeout")
    return None
