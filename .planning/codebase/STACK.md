# Technology Stack

## Languages & Runtimes

| Language | Version | Usage |
|----------|---------|-------|
| Python | 3.12 | Backend server, automation logic, platform plugins |
| TypeScript | 5.9 | Frontend React application |
| Bash | - | Docker entrypoint, build scripts |

**Runtime:**
- Python 3.12-slim (Docker production)
- Node.js 20 (frontend build only, not runtime)

## Frameworks & Libraries

### Backend (Python)

| Framework/Package | Version | Purpose |
|-------------------|---------|---------|
| **FastAPI** | ≥0.110.0 | REST API server, WebSocket support |
| **Uvicorn** | ≥0.29.0 | ASGI server for FastAPI |
| **SQLModel** | ≥0.0.16 | ORM (SQLAlchemy + Pydantic hybrid) |
| **Pydantic** | ≥2.0.0 | Data validation and serialization |
| **Quart** | ≥0.19.0 | Async HTTP server for Turnstile solver subprocess |
| **PyInstaller** | ≥6.0.0 | Desktop app packaging (executable bundling) |

### Browser Automation

| Package | Version | Purpose |
|---------|---------|---------|
| **Playwright** | ≥1.43.0 | Headless/headed Chromium browser automation |
| **Patchright** | ≥1.0.0 | Anti-detection patched Playwright fork |
| **Camoufox** | ≥0.4.0 | Firefox-based anti-fingerprint browser |
| **curl_cffi** | ≥0.6.0 | TLS-fingerprint-accurate HTTP client (impersonates Chrome) |

### Frontend (React)

| Package | Version | Purpose |
|---------|---------|---------|
| **React** | 19.2.4 | UI framework |
| **React Router** | 7.13.1 | Client-side routing |
| **Vite** | 8.0.0 | Build tool and dev server |
| **Tailwind CSS** | 4.2.2 | Utility-first CSS framework |
| **Radix UI** | various | Headless UI primitives (Dialog, Select, Tabs, Toast, Dropdown) |
| **Lucide React** | 0.577.0 | Icon library |
| **class-variance-authority** | 0.7.1 | Component variant management |

### Desktop (Electron)

| Package | Version | Purpose |
|---------|---------|---------|
| **Electron** | 33.0.0 | Desktop app wrapper |
| **electron-builder** | 25.0.0 | Cross-platform packaging (DMG, NSIS, AppImage) |
| **electron-updater** | 6.3.0 | Auto-update from GitHub Releases |

### Security & Crypto

| Package | Version | Purpose |
|---------|---------|---------|
| **jwcrypto** | ≥1.5.0 | JWT/JWK handling for platform OAuth |
| **pyotp** | ≥2.9.0 | TOTP 2FA code generation |
| **cbor2** | ≥5.4.0 | CBOR encoding (WebAuthn/security keys) |

### Testing

| Package | Version | Purpose |
|---------|---------|---------|
| **pytest** | ≥8.0.0 | Test runner |
| **httpx** | ≥0.27.0 | Async HTTP client for API testing |

## Databases & Storage

| Database | Type | Connection |
|----------|------|------------|
| **SQLite** | Embedded relational | `ACCOUNT_MANAGER_DATABASE_URL` env var (default: `sqlite:///account_manager.db`) |
| **SQLite** (Portal) | Embedded relational | `PORTAL_DATABASE_URL` env var (default: `sqlite:///customer_portal.db`) |

**ORM:** SQLModel (SQLAlchemy core + Pydantic models)

**Tables (main DB):** `accounts`, `account_overviews`, `account_credentials`, `provider_accounts`, `provider_resources`, `provider_definitions`, `provider_settings`, `platform_capability_overrides`, `task_logs`, `tasks`, `task_events`, `proxies`

**Tables (portal DB):** `portal_users`, `portal_roles`, `portal_permissions`, `portal_role_permissions`, `portal_platforms`, `portal_products`, `portal_subscriptions`, `portal_orders`, `portal_payment_records`, `portal_tasks`, `portal_task_events`, `portal_task_logs`, `portal_accounts`, `portal_config`, `portal_proxies`, `refresh_tokens`, `user_platform_access`

## Infrastructure & DevOps

| Tool | Purpose |
|------|---------|
| **Docker** | Multi-stage build (Node frontend → Python backend) |
| **docker-compose** | Local development orchestration |
| **GitHub Actions** | CI/CD: build & release (macOS, Windows, Docker, GitHub Release) |
| **Xvfb** | Virtual display for headed browser in Docker |
| **x11vnc + noVNC** | Remote browser preview (port 6080) |

**Docker ports exposed:**
- `8000` — FastAPI + Web UI
- `6080` — noVNC (browser preview)
- `8889` — Turnstile Solver subprocess

## Development Tools

| Tool | Purpose |
|------|---------|
| **Vite** | Frontend dev server with HMR, proxy to `localhost:8000` |
| **ESLint** | Frontend linting |
| **Rich** | Terminal UI formatting for solver subprocess |

## Key Configuration Files

| File | Purpose |
|------|---------|
| `requirements.txt` | Python dependencies (main app) |
| `frontend/package.json` | Frontend dependencies and scripts |
| `electron/package.json` | Electron app config |
| `electron/electron-builder.yml` | Desktop packaging config |
| `Dockerfile` | Multi-stage production build |
| `docker-compose.yml` | Local dev environment |
| `pytest.ini` | Test configuration (`testpaths = tests`, `pythonpath = .`) |
| `.github/workflows/release.yml` | CI/CD pipeline |

## Key Architectural Patterns

- **Provider Registry:** Plugin-based system at `providers/registry.py` with `@register_provider()` decorator for mailbox, SMS, captcha, and proxy providers
- **Platform Plugins:** Modular platform implementations at `platforms/` (Cursor, ChatGPT, Windsurf, Trae, Kiro, Grok, Cerebras, etc.)
- **Dual Database:** Separate SQLite databases for main app and customer portal
- **Subprocess Architecture:** Turnstile solver runs as separate Quart process (port 8889), managed by `services/solver_manager.py`
- **Anti-Detection:** Uses `curl_cffi` for TLS fingerprinting, `camoufox` for browser fingerprint evasion, `patchright` for Playwright patches

## Platform Support

**Supported automation platforms:** Cursor, ChatGPT, Windsurf, Trae, Kiro, Grok, Cerebras, Kimchi, Tavily, Fireworks, OpenBlockLabs, Blackbox, Blink, Anything

**Registration methods:** Browser automation (Playwright/Patchright/Camoufox), Protocol-based API, OAuth flows

---

*Stack analysis: 2026-06-26*
