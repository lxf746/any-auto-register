# External Integrations

## APIs & External Services

### SMS Verification Providers

| Provider | Base URL | Auth | Purpose |
|----------|----------|------|---------|
| **SMS-Activate** | `https://api.sms-activate.guru/stubs/handler_api.php` | API Key | Phone number rental for SMS verification |
| **HeroSMS** | `https://hero-sms.com/stubs/handler_api.php` | API Key | Phone number rental with phone reuse/caching |
| **SMSBower** | `https://smsbower.page/stubs/handler_api.php` | API Key | SMS verification (HeroSMS-compatible API) |

**Implementation:** `core/base_sms.py` — `SmsActivateProvider`, `HeroSmsProvider`, `SmsBowerProvider`

### Temporary Mailbox Providers

| Provider | API URL | Auth | Purpose |
|----------|---------|------|---------|
| **TempMail.lol** | `https://api.tempmail.lol/v2` | None | Disposable email addresses |
| **Mail.tm** | `https://api.mail.tm` | Account creation | Temporary email with API |
| **CFWorker** | Cloudflare Worker endpoint | Admin API key | Custom email relay |
| **Laoudo** | `https://laoudo.com/api/email` | API key | Temporary email service |
| **Aitre** | `https://mail.aitre.cc/api/tempmail` | API key | Temporary email service |
| **TestMail** | Custom endpoint | API key | Test email service |
| **TempyEmail** | Custom endpoint | API key | Temporary email |
| **Freemail** | Custom endpoint | API key | Free email provider |
| **DuckMail** | Custom endpoint | API key | DuckDuckGo-based email |
| **DDG Email** | DuckDuckGo Email | None | DuckDuckGo email protection |

**Implementation:** `core/base_mailbox.py` — Abstract base + concrete implementations per provider

### Captcha Solving Services

| Provider | API URL | Auth | Purpose |
|----------|---------|------|---------|
| **YesCaptcha** | `https://api.yescaptcha.com` | Client Key | Cloud Turnstile/ReCAPTCHA solving |
| **2Captcha** | `https://api.2captcha.com` | API Key | Cloud captcha solving |
| **Local Solver** | `http://localhost:8889` | None | Self-hosted Turnstile solver |

**Implementation:** `core/base_captcha.py` — `YesCaptcha`, `TwoCaptcha`, `LocalSolverCaptcha`

### Proxy Providers

| Provider | Type | Purpose |
|----------|------|---------|
| **API Extract** | HTTP API | Fetch proxy IPs from configurable API endpoint |
| **Rotating Gateway** | Gateway URL | Rotating proxy gateway |

**Implementation:** `core/proxy_providers.py`, `providers/proxy/api_extract.py`, `providers/proxy/rotating_gateway.py`

### Platform-Specific Integrations

| Platform | Integration Type | Key Files |
|----------|-----------------|-----------|
| **ChatGPT** | OAuth, Browser automation, Protocol API, Payment, Token refresh | `platforms/chatgpt/` |
| **Cursor** | Browser registration, OAuth, Protocol mailbox, License switching | `platforms/cursor/` |
| **Windsurf** | Browser registration, Protocol mailbox, License switching | `platforms/windsurf/` |
| **Trae** | Browser registration, OAuth, Protocol mailbox | `platforms/trae/` |
| **Kiro** | Browser registration, OAuth, AWS Event Stream, Protocol mailbox | `platforms/kiro/` |
| **Grok** | Browser registration, OAuth, Protocol mailbox | `platforms/grok/` |
| **Cerebras** | Protocol mailbox | `platforms/cerebras/` |
| **Tavily** | Browser registration, OAuth, Protocol mailbox | `platforms/tavily/` |
| **Fireworks** | Protocol mailbox | `platforms/fireworks/` |
| **OpenBlockLabs** | Browser registration, OAuth, Protocol mailbox | `platforms/openblocklabs/` |
| **Blackbox** | Browser registration, OAuth | `platforms/blackbox/` |
| **Kimchi** | Protocol mailbox | `platforms/kimchi/` |
| **Blink** | Protocol mailbox | `platforms/blink/` |
| **Anything** | Protocol mailbox | `platforms/anything/` |

## Authentication & Authorization

### Main App Auth

- **Type:** Bearer token / Cookie-based simple password auth
- **Implementation:** `core/auth.py` — `AuthMiddleware` (Starlette middleware)
- **Env var:** `APP_PASSWORD` — if set, all `/api` endpoints require `Authorization: Bearer <password>` or cookie `_auth=<password>`
- **Public endpoints:** `/api/health`, `/api/ready`, `/api/auth/`

### Customer Portal Auth

- **Type:** JWT (HS256) with refresh tokens
- **Implementation:** `customer_portal_api/app/security.py`
- **Password hashing:** PBKDF2-SHA256 (200,000 iterations)
- **Token TTL:** Access token configurable via `PORTAL_ACCESS_TOKEN_TTL_SECONDS` (default 7200s), Refresh token via `PORTAL_REFRESH_TOKEN_TTL_SECONDS` (default 30 days)
- **Env vars:** `PORTAL_JWT_SECRET`, `PORTAL_ADMIN_USERNAME`, `PORTAL_ADMIN_PASSWORD`

### Platform OAuth

- **JWK/JWT handling:** `jwcrypto` library for platform-specific OAuth flows (e.g., ChatGPT, Cursor)
- **TOTP 2FA:** `pyotp` library for generating TOTP codes during registration
- **CBOR/WebAuthn:** `cbor2` library for security key interactions

## HTTP Clients

### Primary: curl_cffi

- **Usage:** TLS-fingerprint-accurate HTTP requests impersonating Chrome
- **Config:** `core/http_client.py` — `HTTPClient` class with proxy, retry, and session management
- **Impersonation:** `chrome136` (configurable)
- **Files:** `core/http_client.py`, used extensively in `platforms/*/` modules

### Secondary: requests

- **Usage:** Standard HTTP requests for provider APIs (SMS, mailbox, captcha)
- **Files:** `core/base_sms.py`, `core/base_mailbox.py`, `providers/` modules

### Tertiary: httpx

- **Usage:** Async HTTP client for testing
- **Files:** `tests/`

## Data Storage

### SQLite (Main App)

- **Database file:** `account_manager.db` (configurable via `ACCOUNT_MANAGER_DATABASE_URL`)
- **ORM:** SQLModel (SQLAlchemy + Pydantic)
- **Connection:** Single-threaded, WAL mode implied
- **Schema management:** Auto-migration in `core/db.py` — `init_db()` with column addition and legacy data migration

### SQLite (Customer Portal)

- **Database file:** `customer_portal.db` (configurable via `PORTAL_DATABASE_URL`)
- **ORM:** SQLModel
- **Connection:** `check_same_thread=False` for SQLite

### File Storage

- **Type:** Local filesystem only
- **Data directory:** `./data/` (Docker volume mount)
- **Cache files:** HeroSMS phone cache (`data/.herosms_phone_cache.json`)

## Browser Automation

### Playwright

- **Purpose:** Headless/headed Chromium automation for registration flows
- **Implementation:** `core/executors/playwright.py` — `PlaywrightExecutor`
- **Config:** Viewport 1280x720, 60s default timeout, anti-automation-detection flags

### Patchright

- **Purpose:** Anti-detection Playwright fork for stealth browser automation
- **Usage:** Turnstile solver subprocess (`services/turnstile_solver/api_solver.py`)

### Camoufox

- **Purpose:** Firefox-based anti-fingerprint browser
- **Usage:** Turnstile solver subprocess (default browser mode)
- **Binary management:** Auto-download via `camoufox.pkgman`

## Monitoring & Observability

- **Logging:** Python standard `logging` module
- **Terminal UI:** `rich` library for solver subprocess console output
- **Health checks:** `/api/health`, `/api/ready` endpoints (public, no auth required)

## Webhooks & Callbacks

### Incoming

- **Payment callbacks:** `customer_portal_api/app/routers/payment.py` — `POST /api/payment/callback/{channel_code}`
- **Purpose:** Handle payment provider notifications (generic payload format)

### Outgoing

- **None detected** — system is polling-based, not push-based

## Build & Distribution

### GitHub Actions CI/CD

- **Triggers:** Tag push (`v*`)
- **Builds:** macOS (DMG/ZIP), Windows (NSIS), Docker (GHCR), GitHub Release
- **Artifacts:** PyInstaller-bundled backend + Electron desktop app

### Docker

- **Registry:** GitHub Container Registry (`ghcr.io`)
- **Base images:** `python:3.12-slim` (backend), `node:20-slim` (frontend build)
- **Browser deps:** Chromium, Xvfb, x11vnc, noVNC

### Electron

- **Packaging:** electron-builder
- **Targets:** macOS (DMG/ZIP), Windows (NSIS), Linux (AppImage)
- **Auto-update:** GitHub Releases via `electron-updater`

---

*Integration audit: 2026-06-26*
