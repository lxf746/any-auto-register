# Any Auto Register

<p align="center">
  <a href="https://github.com/lxf746/any-auto-register/stargazers"><img src="https://img.shields.io/github/stars/lxf746/any-auto-register?style=for-the-badge&logo=github&color=FFB003" alt="Stars" /></a>
  <a href="https://github.com/lxf746/any-auto-register/network/members"><img src="https://img.shields.io/github/forks/lxf746/any-auto-register?style=for-the-badge&logo=github&color=blue" alt="Forks" /></a>
  <a href="https://github.com/lxf746/any-auto-register/releases"><img src="https://img.shields.io/github/v/release/lxf746/any-auto-register?style=for-the-badge&logo=github&color=green" alt="Release" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/lxf746/any-auto-register?style=for-the-badge&color=orange" alt="License" /></a>
</p>

<p align="center">
  <a href="README.md">中文</a> |
  <b>English</b> |
  <a href="README_vi.md">Tiếng Việt</a>
</p>

<p align="center">
  <b>Multi-platform account auto-registration & management system · 13+ platforms · 9+ mailbox services · Protocol/Browser dual-mode · One-click desktop app</b>
</p>

<a href="https://bestproxy.com/?keyword=l85nsbgw" target="_blank"><img src="assets/bestproxy.gif" alt="BestProxy - High-purity residential IPs with one-account-per-IP isolation, full-link anti-correlation, significantly boosting account approval rates and long-term survival" width="100%"></a>

> ⚠️ **Disclaimer**: This project is for learning and research purposes only. It must not be used for any commercial purposes. Users are solely responsible for any consequences arising from the use of this project.

> 🌟 **This is the official upstream of [`lxf746/any-auto-register`](https://github.com/lxf746/any-auto-register)** — the original author's repository with the most timely updates. Other repositories with the same name are forks.

A multi-platform account auto-registration and management system with plugin-based extensibility and a built-in Web UI.

<a href="https://legionproxy.io/?utm_source=github&utm_campaign=any-auto-register" target="_blank"><img src="assets/legionproxy.png" alt="LegionProxy - Residential proxies built for account registration and automation, 74M+ real residential IPs, 195+ countries, HTTP/3 high-speed connection, starting at $0.60/GB" width="100%"></a>

[LegionProxy — Residential proxies built for account registration and automation · 74M+ real residential IPs · 195+ countries · HTTP/3 · From $0.60/GB](https://legionproxy.io/?utm_source=github&utm_campaign=any-auto-register)

## Table of Contents

- [Highlights](#highlights)
- [Features](#features)
- [Screenshots](#screenshots)
- [Tech Stack](#tech-stack)
- [Desktop Download](#desktop-download)
- [Quick Start](#quick-start)
- [Docker Deployment](#docker-deployment)
- [Mailbox Providers](#mailbox-providers)
- [Captcha Providers](#captcha-providers)
- [Proxy Pool](#proxy-pool)
- [SMS Providers](#sms-providers)
- [Account Lifecycle](#account-lifecycle)
- [Stats Dashboard](#stats-dashboard)
- [Any2API Integration](#any2api-integration)
- [Plugin Development](#plugin-development)
- [FAQ](#faq)
- [Sponsors](#sponsors)
- [Community](#community)
- [Star History](#star-history)
- [License](#license)

## Highlights

Why choose any-auto-register over alternatives:

| Capability | any-auto-register | Other tools |
|------|------|------|
| 🖥️ **One-click desktop app** | ✅ Mac / Windows Electron client, no CLI required | ❌ Usually CLI / Docker only |
| 🧩 **Platform coverage** | ✅ 13+ platforms out-of-the-box + generic Anything adapter | Usually 1-3 platforms |
| 📨 **Mailbox services** | ✅ 9 services (self-hosted + public + DDG) | Usually 1-2 |
| ⚡ **Three execution modes** | ✅ Pure protocol (no browser, fastest) / headless / headed | Usually browser-only |
| 🔁 **Account lifecycle** | ✅ Validity check, token auto-refresh, trial expiration warning | ❌ Most only register |
| 📊 **Success-rate dashboard** | ✅ Per-platform / per-proxy / per-day stats, error aggregation | ❌ |
| 🔌 **Any2API integration** | ✅ Register-and-use, auto-push to gateway | ❌ |
| 📦 **Plugin architecture** | ✅ Platform / mailbox / captcha / SMS / proxy all pluggable | Usually hardcoded |

> 💡 Combine [`Any2API`](https://github.com/lxf746/any2api) gateway + `any-auto-register` to enable a full pipeline: **bulk-register accounts → auto-push to gateway → instantly use as OpenAI/Claude-compatible API**.

## Features

- **Multi-platform**: ChatGPT, Cursor, Kiro, Trae.ai, Tavily, Grok, Blink, Cerebras, OpenBlockLabs, Windsurf, plus a generic Anything adapter for custom plugins
- **Multi-mailbox**: MoeMail (self-hosted), Laoudo, DuckMail, Testmail, Cloudflare Worker self-hosted, Freemail, TempMail.lol, Temp-Mail Web, DuckDuckGo Email
- **Multi-mode execution**: API protocol (no browser) / headless browser / headed browser (per-platform support)
- **Captcha**: YesCaptcha, 2Captcha, local Solver (Camoufox)
- **SMS**: SMS-Activate, HeroSMS (for platforms requiring phone verification)
- **Proxy pool**: static round-robin + dynamic API extraction + rotating gateway, success-rate weighting, auto-disable failed proxies
- **Account lifecycle**: scheduled validity checks, automatic token refresh, trial expiration warnings
- **Success-rate dashboard**: stats by platform, day, and proxy; error aggregation
- **Concurrent registration**: configurable concurrency
- **Real-time logs**: SSE streaming to frontend
- **Account export**: JSON, CSV, CPA, Sub2API, Kiro-Go, Any2API formats
- **Any2API sync**: auto-push registered accounts to Any2API gateway, ready to use immediately
- **Per-platform actions**: customizable actions like Kiro account switching, Trae Pro upgrade-link generation

## Screenshots

> 📸 *Screenshots will be updated with each release. For a full demo, try the [Desktop Download](#desktop-download).*

### Dashboard
![Dashboard](assets/screenshots/dashboard.png)

### Registration Task
![Registration Task](assets/screenshots/register-task.png)

### Settings
![Settings](assets/screenshots/settings.png)

### Accounts
![Accounts](assets/screenshots/accounts.png)

## Tech Stack

| Layer | Technology |
|------|------|
| Backend | FastAPI + SQLite (SQLModel) |
| Frontend | React + TypeScript + Vite + TailwindCSS |
| HTTP | curl_cffi (browser fingerprint spoofing) |
| Browser automation | Playwright / Camoufox |

## Desktop Download

> 🚀 **Zero-config one-click**: Skip Python and Node.js — just download the desktop client and double-click.

| Platform | Download |
|------|------|
| 🍎 macOS (Intel / Apple Silicon) | [Get `.dmg` from Releases](https://github.com/lxf746/any-auto-register/releases/latest) |
| 🪟 Windows | [Get `.exe` from Releases](https://github.com/lxf746/any-auto-register/releases/latest) |

The desktop client bundles the full Python backend + React frontend via Electron — works out of the box. Each new version (`v*` tag) is auto-built and published to [Releases](https://github.com/lxf746/any-auto-register/releases).

## Quick Start

### Requirements

- Python 3.11+
- Node.js 18+

### Install

#### macOS / Linux

```bash
git clone https://github.com/lxf746/any-auto-register.git
cd any-auto-register

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

cd frontend && npm install && npm run build && cd ..
```

#### Windows

```bat
git clone https://github.com/lxf746/any-auto-register.git
cd any-auto-register

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt

cd frontend
npm install
npm run build
cd ..
```

### Install browsers (optional, required for headless/headed modes)

```bash
python3 -m playwright install chromium
python3 -m camoufox fetch
```

### Run

```bash
.venv/bin/python3 -m uvicorn main:app --port 8000
```

Open `http://localhost:8000` in your browser.

## Docker Deployment

```bash
docker compose up -d
```

Open `http://localhost:8000`. The database is persisted to `./data/`.

For headed browser mode, view automation via noVNC at `http://localhost:6080`.

## Mailbox Providers

Pick a mailbox service to receive verification codes. All providers are managed via the **Settings → Providers** page in the Web UI:

- **MoeMail** (recommended): self-hosted on Cloudflare via [cloudflare_temp_email](https://github.com/dreamhunter2333/cloudflare_temp_email)
- **Laoudo**: stable custom-domain mailboxes
- **Cloudflare Worker self-hosted**: full control, deploy your own
- **DuckMail / TempMail.lol / Temp-Mail Web**: public temp-mail services
- **DuckDuckGo Email**: `@duck.com` aliases via DDG Email Protection (requires forwarding IMAP)
- **Freemail**: Cloudflare Worker-based, supports admin token + username/password auth
- **Testmail**: `testmail.app` namespace mode, ideal for concurrent tasks

Detailed field references are available in the Web UI's provider editor and in the [Chinese README](README.md#邮箱服务配置).

## Captcha Providers

| Service | Notes |
|------|------|
| YesCaptcha | Sign up at [yescaptcha.com](https://yescaptcha.com) for a Client Key |
| 2Captcha | Sign up at [2captcha.com](https://2captcha.com) for an API Key |
| Local Solver | Uses Camoufox locally, run `python3 -m camoufox fetch` first |

## Proxy Pool

The system supports both static and dynamic proxies:

- **Static proxies**: managed in the Proxy page; weighted by success rate; auto-disabled after 5 consecutive failures
- **Dynamic proxies**: API-extraction or rotating-gateway providers (BrightData, Oxylabs, IPRoyal, etc.); falls back to static pool on failure

## SMS Providers

For platforms requiring phone verification (e.g., Cursor):

| Service | Notes |
|------|------|
| SMS-Activate | API key + default country |
| HeroSMS | API key + service code, country ID, max price, number reuse policy |

## Account Lifecycle

Built-in background lifecycle manager runs:

- **Validity check** every 6h — invalid accounts marked
- **Token refresh** every 12h — auto-refreshes expiring tokens (currently ChatGPT)
- **Trial warning** — flags accounts nearing expiration

Manual triggers:

- `POST /api/lifecycle/check` — manual validity check
- `POST /api/lifecycle/refresh` — manual token refresh
- `POST /api/lifecycle/warn` — manual trial warning
- `GET /api/lifecycle/status` — manager status

## Stats Dashboard

Query registration stats via API:

- `GET /api/stats/overview` — global overview
- `GET /api/stats/by-platform` — per-platform success rate
- `GET /api/stats/by-day?days=30` — daily trends
- `GET /api/stats/by-proxy` — proxy success ranking
- `GET /api/stats/errors?days=7` — error aggregation

## Any2API Integration

Pair with [Any2API](https://github.com/lxf746/any2api) — registered accounts are auto-pushed to the gateway, ready to use immediately as OpenAI/Claude-compatible APIs.

Configure in Settings:

| Field | Description |
|------|------|
| `any2api_url` | Any2API instance URL, e.g. `http://localhost:8099` |
| `any2api_password` | Any2API admin password |

Push targets per platform: Kiro → `kiroAccounts`, Grok → `grokTokens`, Cursor → `cursorConfig`, ChatGPT → `chatgptConfig`, Blink → `blinkConfig`, Windsurf → `windsurfAccounts`.

If `any2api_url` is not set, this integration is silently skipped.

## Plugin Development

Adding a new platform:

1. Create `platforms/myplatform/` with `__init__.py` and `plugin.py`
2. Implement a `BasePlatform` subclass and decorate it with `@register`
3. Declare capabilities (`supported_executors`, `supported_identity_modes`, etc.)

```python
from core.base_platform import BasePlatform, AccountStatus
from core.registry import register

@register
class MyPlatform(BasePlatform):
    name = "myplatform"
    display_name = "My Platform"
    version = "1.0.0"
    supported_executors = ["protocol"]
    supported_identity_modes = ["mailbox"]

    def check_valid(self, account) -> bool:
        return bool(account.token)
```

The platform auto-loads on startup. See the [Chinese README](README.md#插件开发) for full implementation details.

## FAQ

**Captcha keeps failing?**
Verify your captcha provider is configured correctly. In protocol mode, prefer YesCaptcha/2Captcha. In browser mode, Camoufox tries the Turnstile checkbox first and falls back to remote solvers. If failures persist, check proxy IP quality — high-risk IPs trigger stricter challenges.

**Proxies getting banned / low success rate?**
Use residential proxies over datacenter IPs. Lower concurrency. Check per-proxy stats in the Proxy page and disable low-performers. Different platforms have different IP sensitivity — consider per-platform proxy pools.

**Browser mode setup?**
```bash
python3 -m playwright install chromium
python3 -m camoufox fetch
```

**Solver startup timeout?**
The local Turnstile Solver needs Camoufox installed. Run `python3 -m camoufox fetch` first, then click "Restart Solver" in the Settings page. Or skip local Solver entirely and use YesCaptcha / 2Captcha.

## Sponsors

Thanks to the following sponsors for their long-term support of any-auto-register. If your service targets account registration, automation, or AI developers, feel free to reach out.

| Logo | Name | Description | Link |
| --- | --- | --- | --- |
| <a href="https://bestproxy.com/?keyword=l85nsbgw" target="_blank"><img src="assets/bestproxy.gif" alt="BestProxy" width="140" /></a> | **BestProxy** | High-purity residential IPs with one-account-per-IP isolation, full-link anti-correlation, significantly boosting approval rates and long-term survival. | [bestproxy.com](https://bestproxy.com/?keyword=l85nsbgw) |
| <a href="https://legionproxy.io/?utm_source=github&utm_campaign=any-auto-register" target="_blank"><img src="assets/legionproxy.png" alt="LegionProxy" width="140" /></a> | **LegionProxy** | Residential proxies built for account registration and automation, 74M+ real residential IPs, 195+ countries, HTTP/3 high-speed connection, from $0.60/GB. | [legionproxy.io](https://legionproxy.io/?utm_source=github&utm_campaign=any-auto-register) |

## Community

Join the user group for updates, configuration tips, and registration know-how:

### QQ Group (recommended)

**Group ID: `1081650009`**

<a href="assets/qq-group.png" target="_blank"><img src="assets/qq-group.png" alt="QQ Group QR Code" width="220" /></a>

Scan the QR code above or search the group ID to join.

For bugs and feature requests, please use [Issues](https://github.com/lxf746/any-auto-register/issues).

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=lxf746/any-auto-register&type=Date)](https://star-history.com/#lxf746/any-auto-register&Date)

## License

This project is licensed under [AGPL-3.0](LICENSE). Personal learning and research are unrestricted; commercial use must comply with AGPL-3.0 (derivative works must be open-sourced).
