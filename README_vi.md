<div align="center">

# Any Auto Register

Tự động hóa tài khoản cho 11+ nền tảng AI · Chế độ giao thức / trình duyệt · Khởi động một chạm trên Mac / Windows

<p>
  <a href="https://github.com/lxf746/any-auto-register/stargazers"><img src="https://img.shields.io/github/stars/lxf746/any-auto-register?style=flat-square&logo=github&color=FFB003" alt="Stars" /></a>
  <a href="https://github.com/lxf746/any-auto-register/releases/latest"><img src="https://img.shields.io/github/v/release/lxf746/any-auto-register?style=flat-square&logo=github&color=22c55e" alt="Release" /></a>
  <a href="https://github.com/lxf746/any-auto-register/releases"><img src="https://img.shields.io/github/downloads/lxf746/any-auto-register/total?style=flat-square&logo=github&color=8b5cf6" alt="Downloads" /></a>
  <a href="https://github.com/lxf746/any-auto-register/network/members"><img src="https://img.shields.io/github/forks/lxf746/any-auto-register?style=flat-square&logo=github&color=3b82f6" alt="Forks" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/lxf746/any-auto-register?style=flat-square&color=f97316" alt="License" /></a>
</p>

<p>
  <a href="https://github.com/lxf746/any-auto-register/releases/latest"><b>Tải bản desktop</b></a>
  &nbsp;·&nbsp;
  <a href="#vấn-đề-được-giải-quyết">Vấn đề được giải quyết</a>
  &nbsp;·&nbsp;
  <a href="#xem-nhanh">Ảnh chụp</a>
  &nbsp;·&nbsp;
  <a href="#cộng-đồng">Cộng đồng</a>
  &nbsp;·&nbsp;
  <a href="README.md">中文</a>
  &nbsp;·&nbsp;
  <a href="README_en.md">English</a>
</p>

<img src="assets/screenshots/概览.png" alt="Any Auto Register Dashboard" width="92%" />

</div>

---

> **Đây là kho chính thức của [`lxf746/any-auto-register`](https://github.com/lxf746/any-auto-register)** — kho gốc của tác giả với các cập nhật mới nhất. Các kho cùng tên khác đều là fork.

> Dự án chỉ dành cho học tập và nghiên cứu, không được sử dụng cho mục đích thương mại trái phép. Người dùng có trách nhiệm tự đánh giá và tuân thủ điều khoản dịch vụ của các nền tảng đích, đồng thời tự chịu trách nhiệm về mọi hậu quả phát sinh khi sử dụng.

## Vấn đề được giải quyết

Đa số dự án cùng loại chỉ trả lời *"đăng ký một nền tảng như thế nào"* và bỏ ngỏ phần kỹ thuật còn lại: quản lý email, vượt captcha, xoay proxy, duy trì tài khoản sau đăng ký, refresh token hết hạn, định vị lỗi. Any Auto Register xử lý tất cả.

| | Công cụ khác | Any Auto Register |
|---|---|---|
| Triển khai | CLI / Docker / script `.py` | Desktop client (Mac / Win), nhấp đôi là chạy, UI React tích hợp |
| Độ phủ nền tảng | 1-3 | 11+ nền tảng + Anything adapter tổng quát, mở rộng kiểu plugin |
| Giải pháp email | Chủ yếu IMAP | 9 kênh: MoeMail / Cloudflare tự host / TempMail / DDG Email, v.v. |
| Chế độ thực thi | Chỉ trình duyệt | Pure protocol (nhanh nhất) / Headless / Headed |
| Vòng đời đầy đủ | Đăng ký xong là bỏ | Kiểm tra định kỳ + refresh token + cảnh báo trial + cảnh báo rủi ro |
| Phân tích dữ liệu | Không | Dashboard tỷ lệ thành công, quy lỗi (proxy bị chặn / email lỗi / xác minh phụ) |
| Đồng bộ API gateway | Không | Tự đẩy lên [Any2API](https://github.com/lxf746/any2api), tầng giao thức tương thích OpenAI thống nhất |
| Kiến trúc | Thường hardcode | Pluggable hoàn toàn: platform / mailbox / captcha / SMS / proxy đều cắm rời |

Kết hợp với gateway [`Any2API`](https://github.com/lxf746/any2api) cho pipeline đầy đủ: **đăng ký hàng loạt → tự đẩy → dùng ngay như API tương thích OpenAI / Claude**.

## Xem nhanh

> Ảnh chụp từ bản desktop mới nhất (`v1.0.29`), cập nhật theo từng phiên bản. Ảnh Hero phía trên là dashboard Tổng quan — sáu chỉ số thời gian thực (tổng tài khoản / còn sống / lỗi / đăng ký hôm nay / hàng đợi / số lần thử lại), kèm view kép tỷ lệ thành công + giám sát vòng đời và panel tóm tắt môi trường máy. Dưới đây là các workspace còn lại:

### Account pool — quản lý tài khoản đa nền tảng

Tab theo từng nền tảng, hiển thị mật khẩu / người quản lý / trạng thái / hạn mức / link thanh toán / lần truy vấn gần nhất. Hỗ trợ tìm kiếm, import / export hàng loạt, copy từng dòng, mở link thanh toán.

![Account pool](assets/screenshots/账号池.png)

### Task queue — đăng ký hàng loạt và lịch sử

Toàn bộ tác vụ và tác vụ đang chạy trong một chỗ. Mỗi thẻ hiển thị nền tảng, số thành công / tổng, timestamp, trạng thái. Tạm dừng toàn bộ, dọn hàng đợi, hoặc mở log trực tiếp của từng tác vụ.

![Task queue](assets/screenshots/任务队列.png)

### Log đăng ký — truy vết từng bước

Mọi bước trong luồng đăng ký được stream về frontend qua SSE — đổi OAuth code, lấy token, truy vấn hạn mức — tất cả đều nhìn thấy. Khi lỗi xảy ra, bạn biết chính xác ở bước nào.

![Log đăng ký](assets/screenshots/注册.png)

### Cài đặt — tùy chọn cho desktop

Theme / ngôn ngữ / proxy mặc định toàn cục, kèm các tùy chọn chỉ có ở desktop: khởi động cùng máy, minimize xuống tray, đóng-xuống-tray, kiểm tra cập nhật khi khởi động, thư mục auto-backup.

![Cài đặt](assets/screenshots/设置.png)

## Năng lực cốt lõi

Phân nhóm theo trách nhiệm:

**Luồng đăng ký**

- **Nền tảng**: ChatGPT / Cursor / Kiro / Trae.ai / Tavily / Grok / Blink / Cerebras / OpenBlockLabs / Windsurf, kèm Anything adapter tổng quát
- **Email**: MoeMail tự host / Cloudflare Worker tự host / Laoudo / DuckMail / Testmail / Freemail / TempMail.lol / Temp-Mail Web / DuckDuckGo Email
- **Captcha**: YesCaptcha / 2Captcha / Solver cục bộ (Camoufox)
- **SMS**: SMS-Activate / HeroSMS
- **Chế độ thực thi**: protocol (không browser, nhanh nhất) / Headless / Headed, chuyển đổi theo nền tảng
- **2FA cục bộ**: TOTP tích hợp sẵn, không cần app bên thứ ba

**Vận hành**

- **Vòng đời**: kiểm tra hợp lệ định kỳ + tự refresh token + cảnh báo trial, refresh một chạm từ dashboard
- **Trung tâm rủi ro**: cảnh báo tập trung *Token hết hạn* / *Trial sắp cạn* / *Proxy không kết nối được*
- **Thống kê tỷ lệ thành công**: tỷ lệ toàn cục + quy lỗi (thành công ngay / xác minh phụ / proxy bị chặn / email lỗi), tách theo nền tảng / ngày / proxy
- **Hàng đợi tác vụ**: lịch sử đăng ký hàng loạt + tiến độ thời gian thực + log từng tác vụ

**Hệ thống**

- **Proxy pool**: static (weight theo tỷ lệ thành công) + API extraction động + rotating gateway, tự vô hiệu hóa khi lỗi
- **Đồng bộ Any2API**: tự đẩy tài khoản đăng ký lên gateway — dùng được ngay
- **Định dạng export**: JSON / CSV / CPA / Sub2API / Kiro-Go / Any2API `admin.json`
- **Concurrency & log**: concurrency cấu hình được, SSE log trực tiếp, task runner bền vững
- **Kiến trúc plugin**: platform / mailbox / captcha / SMS / proxy driver — đều cắm rời

## Bắt đầu nhanh

### Desktop (khuyến nghị)

> 🚀 Zero config. Electron đóng gói sẵn cả backend + frontend, nhấp đôi là chạy.

| Nền tảng | Tải xuống |
|------|------|
| 🍎 macOS (Intel / Apple Silicon) | [Tải `.dmg` từ Releases](https://github.com/lxf746/any-auto-register/releases/latest) |
| 🪟 Windows | [Tải `.exe` từ Releases](https://github.com/lxf746/any-auto-register/releases/latest) |

Cài → khởi động → nhập activation code ([nhận từ nhóm](#cộng-đồng)) → chọn nền tảng → cấu hình email → bắt đầu đăng ký.

### Docker

```bash
mkdir -p any-auto-register && cd any-auto-register

cat > docker-compose.yml <<'EOF'
services:
  app:
    image: ghcr.io/lxf746/any-auto-register:latest
    ports:
      - "8000:8000"   # Web UI
      - "6080:6080"   # noVNC (xem browser)
      - "8889:8889"   # Turnstile Solver
    environment:
      - DISPLAY=:99
      # - APP_PASSWORD=changeme
    volumes:
      - ./data:/app/data
    restart: unless-stopped
EOF

docker compose up -d
```

| Dịch vụ | URL | Ghi chú |
|------|------|------|
| Web UI | `http://localhost:8000` | Giao diện chính |
| noVNC | `http://localhost:6080/vnc.html` | Xem browser (chế độ headed) |
| Solver | `http://localhost:8889` | Bộ giải Turnstile captcha |

Khi triển khai cloud, mở port `8000` / `6080` / `8889`.

### Từ mã nguồn

> Mã nguồn bao gồm luồng đăng ký cốt lõi và toàn bộ hệ provider — phù hợp để tự host và mở rộng. Kiểm soát hàng đợi tác vụ nâng cao, quản lý activation code, tăng cường luồng thanh toán, và các bản thích ứng nền tảng mới nhất chỉ đi kèm bản desktop.

Yêu cầu Python 3.11+ / Node.js 18+:

```bash
git clone https://github.com/lxf746/any-auto-register.git
cd any-auto-register/account_manager

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cd frontend && npm install && npm run build && cd ..

# Tùy chọn — cần cho chế độ browser
python3 -m playwright install chromium
python3 -m camoufox fetch

python3 -m uvicorn main:app --port 8000
```

Mở `http://localhost:8000`. Frontend hot-reload xem mục [Phát triển](#phát-triển).

## Cấu hình

### Provider email

Chọn một dịch vụ email để nhận mã xác minh. Cấu hình email, captcha, SMS đều do provider catalog ở backend điều khiển — trang **Settings** trong Web UI là CRUD dạng danh sách: cấu hình hiện có ở bên trái, editor thống nhất ở bên phải. Provider mới thêm ở backend sẽ tự xuất hiện sau khi refresh — không cần sửa frontend.

| Provider | Ghi chú |
|----------|------|
| **MoeMail** (khuyến nghị) | Temp mail tự host dựa trên [cloudflare_temp_email](https://github.com/dreamhunter2333/cloudflare_temp_email). Không cần cấu hình — địa chỉ sinh tự động. |
| **Laoudo** | Email custom-domain cố định. Ổn định nhất, phù hợp dùng lâu dài. |
| **Cloudflare Worker tự host** | Tự deploy dựa trên `cloudflare_temp_email`. Toàn quyền kiểm soát. |
| **Testmail** | Chế độ namespace `testmail.app`, phù hợp tác vụ song song (auto tag + lọc theo timestamp). |
| **DuckDuckGo Email** | Alias `@duck.com` riêng tư + IMAP forwarding. |
| **Freemail** | Cloudflare Worker tự host, hỗ trợ admin token hoặc username / password. |
| **DuckMail** | Temp mail công cộng, không cần cấu hình. Một số khu vực cần proxy. |
| **TempMail.lol** | Temp mail công cộng, tự sinh địa chỉ ẩn danh. |
| **Temp-Mail Web** | Dựa trên `web2.temp-mail.org`. |

Định dạng các trường được mô tả trực tiếp trong editor — backend tự render form từ provider catalog tương ứng.

### Provider captcha

| Dịch vụ | Ghi chú |
|------|------|
| YesCaptcha | Đăng ký tại [yescaptcha.com](https://yescaptcha.com) để lấy Client Key |
| 2Captcha | Đăng ký tại [2captcha.com](https://2captcha.com) để lấy API Key |
| Local Solver | Solver Camoufox cục bộ, chạy `python3 -m camoufox fetch` trước |

### Proxy pool

| 🌟 Proxy đề xuất | Mô tả |
| :--- | :--- |
| <a href="https://www.swiftproxy.net/?ref=lxf746"><img src="assets/swiftproxy.svg" width="130" alt="Swiftproxy"/></a> | **[Swiftproxy](https://www.swiftproxy.net/?ref=lxf746)** — 80M+ IP dân cư chất lượng cao, kết nối ổn định ẩn danh cao, lưu lượng động không hết hạn, hỗ trợ dùng thử miễn phí, hoàn hảo cho xoay proxy tự động. |
| <a href="https://colaproxy.com/?utm_source=lxf746&utm_medium=lxf746&ref=lxf746"><img src="assets/colaproxy.png" width="130" alt="ColaProxy"/></a> | **[ColaProxy](https://colaproxy.com/?utm_source=lxf746&utm_medium=lxf746&ref=lxf746)** — Dùng thử miễn phí 90M+ IP sạch ở nước ngoài, giá từ $0.3/GB. Residential / mobile / static / không giới hạn, rotation tốc độ cao + cách ly đa tài khoản, giảm tỷ lệ bị chặn. |

- **Static proxy** — thêm thủ công ở trang Proxy, weight theo tỷ lệ thành công, tự vô hiệu hóa sau 5 lần lỗi liên tiếp
- **API extraction** — kéo IP động qua HTTP API, hoạt động với hầu hết endpoint của các vendor
- **Rotating gateway** — entry cố định, IP exit khác nhau ở mỗi request — dùng cho BrightData / Oxylabs / IPRoyal, v.v.

Khi `proxy` provider được bật trong database, đăng ký sẽ thử dynamic proxy trước và fallback về static pool nếu lỗi.

### Provider SMS

Cho các nền tảng yêu cầu xác minh số điện thoại (ví dụ Cursor):

| Dịch vụ | Ghi chú |
|------|------|
| SMS-Activate | API key + quốc gia mặc định |
| HeroSMS | API key + service code, country ID, giá tối đa, chính sách reuse số |

Tham số `sms_provider` ở cấp tác vụ ưu tiên hơn; nếu không chỉ định, dùng SMS provider mặc định.

## Nâng cao

### Vòng đời tài khoản

Lifecycle manager nền chạy tự động:

- **Kiểm tra hợp lệ** mỗi 6 giờ — đánh dấu tài khoản không còn hợp lệ
- **Refresh token** mỗi 12 giờ — refresh token sắp hết hạn (hiện hỗ trợ ChatGPT)
- **Cảnh báo trial** — đánh dấu tài khoản sắp hết, cập nhật trạng thái khi đã hết

Trigger thủ công: `POST /api/lifecycle/{check|refresh|warn}`, `GET /api/lifecycle/status` để xem trạng thái.

### Thống kê tỷ lệ thành công & quy lỗi

- `GET /api/stats/overview` — tổng quan toàn cục
- `GET /api/stats/by-platform` — theo nền tảng
- `GET /api/stats/by-day?days=30` — xu hướng theo ngày
- `GET /api/stats/by-proxy` — xếp hạng proxy
- `GET /api/stats/errors?days=7` — quy lỗi tổng hợp

### Tích hợp Any2API

Kết hợp với gateway [Any2API](https://github.com/lxf746/any2api) — tài khoản đăng ký xong được tự đẩy lên và dùng được ngay.

Cấu hình trong Settings:

| Trường | Mô tả |
|------|------|
| `any2api_url` | URL Any2API instance, ví dụ `http://localhost:8099` |
| `any2api_password` | Mật khẩu admin của Any2API |

Đích đẩy theo nền tảng:

| Nền tảng | Đích |
|------|----------|
| Kiro | `kiroAccounts` pool |
| Grok | `grokTokens` pool |
| Cursor | `cursorConfig` cookie |
| ChatGPT | `chatgptConfig` token |
| Blink | `blinkConfig` credentials |
| Windsurf | `windsurfAccounts` pool |

Nếu không đặt `any2api_url`, tích hợp này sẽ được bỏ qua một cách yên lặng.

## Công nghệ

| Tầng | Công nghệ |
|------|------|
| Backend | FastAPI + SQLite (SQLModel) |
| Frontend | React + TypeScript + Vite + TailwindCSS |
| HTTP | curl_cffi (giả lập browser fingerprint) |
| Browser automation | Playwright / Camoufox |
| Desktop | Electron + đóng gói Nuitka |

## Phát triển

<details>
<summary><b>Cấu trúc dự án</b></summary>

```
account_manager/
├── main.py                 # FastAPI entry
├── api/                    # HTTP routes
│   ├── accounts.py         # account CRUD + export
│   ├── account_providers.py     # mailbox / captcha / SMS / proxy
│   ├── registration.py          # registration tasks + SSE
│   ├── query.py                 # truy vấn trạng thái tài khoản
│   ├── payment.py               # link thanh toán / hành động
│   ├── transfer.py              # import / export
│   ├── platforms.py             # danh sách nền tảng
│   ├── provider_definitions.py  # định nghĩa provider
│   ├── proxies.py               # quản lý proxy
│   ├── health.py                # health check
│   └── system.py                # cài đặt hệ thống / Solver
├── application/            # application services
├── domain/                 # domain models
├── infrastructure/         # repositories + runtime adapters
├── core/                   # base classes (platform / mailbox / captcha / SMS)
├── platforms/              # platform plugins
├── providers/              # provider plugins
├── services/               # dịch vụ nền (Solver / task runner)
├── customer_portal_api/    # API người dùng + admin
├── electron/               # đóng gói Electron desktop
├── tests/                  # tests
└── frontend/               # React frontend
```

</details>

<details>
<summary><b>Chế độ phát triển (frontend hot-reload)</b></summary>

```bash
cd frontend
npm run dev
# Mở http://localhost:5173 — Vite proxy API về backend
```

Entry duy nhất là `main:app`. Tất cả route backend nằm dưới `/api/*`. Xem [`docs/frontend-api-contract.md`](docs/frontend-api-contract.md) cho API contract.

</details>

<details>
<summary><b>Thêm platform plugin</b></summary>

Layout plugin:

```
platforms/myplatform/
├── plugin.py
├── registration/
│   ├── module.py       # entry registration module
│   ├── protocol.py     # protocol core
│   ├── worker.py       # mailbox provider → protocol flow
│   ├── browser.py      # browser registration (tùy chọn)
│   └── oauth.py        # browser OAuth (tùy chọn)
├── query.py            # khả năng query (tùy chọn)
├── payment.py          # khả năng payment (tùy chọn)
└── transfer.py         # khả năng import / export (tùy chọn)
```

`plugin.py` tối thiểu:

```python
from core.platform_plugin import ConfiguredPlatformPlugin
from core.plugin_registry import register

@register
class MyPlatformPlugin(ConfiguredPlatformPlugin):
    name = "myplatform"
    display_name = "My Platform"
    version = "2.0.0"
    query_class = "MyPlatformQuery"
    payment_class = "MyPlatformPayment"
    transfer_class = "MyPlatformTransfer"
```

Hệ thống quét `platforms/*/plugin.py` khi khởi động và auto-load mọi thứ đăng ký qua `@register`. Để xem `registration/module.py` đầy đủ, tham khảo các platform có sẵn (`platforms/kiro/`, `platforms/chatgpt/`).

</details>

<details>
<summary><b>Đóng góp</b></summary>

1. Fork kho này
2. Tạo nhánh tính năng: `git checkout -b feature/my-feature`
3. Commit: `git commit -m 'feat: add my feature'` (khuyến nghị [Conventional Commits](https://www.conventionalcommits.org/))
4. Push: `git push origin feature/my-feature`
5. Mở Pull Request

</details>

## Câu hỏi thường gặp

<details>
<summary><b>Captcha liên tục thất bại?</b></summary>

1. Xác nhận provider captcha cấu hình đúng (YesCaptcha Client Key hoặc local Solver)
2. Trong chế độ protocol, ưu tiên dịch vụ remote (YesCaptcha / 2Captcha)
3. Trong chế độ browser, Camoufox thử click Turnstile checkbox trước rồi fallback về remote solver
4. Nếu vẫn lỗi, kiểm tra chất lượng IP proxy — IP rủi ro cao gặp challenge khắt khe hơn

</details>

<details>
<summary><b>Proxy bị chặn / tỷ lệ thành công thấp?</b></summary>

1. Kiểm tra thống kê từng proxy ở trang Proxy và vô hiệu hóa các proxy yếu
2. Dùng residential proxy thay vì IP datacenter
3. Giảm concurrency để tránh burst từ cùng một IP
4. Mỗi nền tảng có độ nhạy IP khác nhau — cân nhắc proxy pool riêng cho từng nền tảng

</details>

<details>
<summary><b>Solver khởi động timeout?</b></summary>

`[Solver] startup timeout` nghĩa là local Turnstile Solver không pass health-check trong 30s. Main service vẫn khởi động. Nguyên nhân thường gặp: Camoufox tải lần đầu, thiếu browser deps, hoặc port `8889` bị chiếm.

1. Chạy `python3 -m camoufox fetch` cục bộ, sau đó click "Restart Solver" trong Settings
2. Để bỏ qua local Solver, cấu hình YesCaptcha hoặc 2Captcha và chọn remote solver ở task config
3. Với Docker, ưu tiên image build sẵn; với bare metal, kiểm tra port `8889` và cài Camoufox

</details>

<details>
<summary><b>Build ARM image lỗi?</b></summary>

Nếu log build hiện `src/pages/Accounts.tsx ... TS6133/TS7006`, lỗi thật ở build TypeScript của frontend — không phải vấn đề ARM hay apt. Chạy cục bộ trước:

```bash
cd frontend && npm run build
```

Sau đó rebuild:

```bash
docker compose build --no-cache && docker compose up -d
```

</details>

## Cộng đồng

Tham gia nhóm người dùng để cập nhật mới nhất, activation code, kinh nghiệm cấu hình và mẹo đăng ký:

| Nhóm QQ | Mã | Trạng thái |
|---|---|---|
| Nhóm 1 | `1081650009` | Đã đầy |
| Nhóm 2 | `1097916468` | Đã đầy |
| Nhóm 3 | `100799970` | Đã đầy |
| Nhóm 4 | `469274724` | Đã đầy |
| Nhóm 5 | `906077873` | Còn chỗ |

Tìm mã nhóm trong QQ để tham gia. Báo bug và yêu cầu tính năng vui lòng dùng [Issues](https://github.com/lxf746/any-auto-register/issues).

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=lxf746/any-auto-register&type=Date)](https://star-history.com/#lxf746/any-auto-register&Date)

> Nếu dự án này giúp bạn tiết kiệm công việc lặp lại, một ⭐ giúp nhiều người khác tìm thấy.

## Nhà tài trợ

<table>
<tr>
<td width="220" align="center">
<a href="https://www.rapidproxy.io/?ref=lxf" target="_blank">
<img src="https://www.rapidproxy.io/static/rapidproxy/images/rapid_logo_700.png" alt="RapidProxy" width="180" />
</a>
</td>
<td>
<b><a href="https://www.rapidproxy.io/?ref=lxf">RapidProxy</a></b> — Proxy dân cư chất lượng cao, xoay IP thông minh, tỷ lệ bị chặn thấp, lưu lượng không hết hạn, hỗ trợ thu thập dữ liệu mạnh mẽ.<br/>
90M+ IP dân cư thực · 200+ quốc gia / khu vực · 99.9% uptime · &lt;0.5s phản hồi.<br/>
<a href="https://www.rapidproxy.io/?ref=lxf"><b>Dùng thử miễn phí →</b></a>
</td>
</tr>
</table>

## Giấy phép

[AGPL-3.0](LICENSE). Học tập và nghiên cứu cá nhân được sử dụng tự do; sử dụng thương mại phải tuân thủ AGPL-3.0 (sản phẩm phái sinh phải open source).
