# Any Auto Register

<p align="center">
  <a href="https://github.com/lxf746/any-auto-register/stargazers"><img src="https://img.shields.io/github/stars/lxf746/any-auto-register?style=for-the-badge&logo=github&color=FFB003" alt="Stars" /></a>
  <a href="https://github.com/lxf746/any-auto-register/network/members"><img src="https://img.shields.io/github/forks/lxf746/any-auto-register?style=for-the-badge&logo=github&color=blue" alt="Forks" /></a>
  <a href="https://github.com/lxf746/any-auto-register/releases"><img src="https://img.shields.io/github/v/release/lxf746/any-auto-register?style=for-the-badge&logo=github&color=green" alt="Release" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/lxf746/any-auto-register?style=for-the-badge&color=orange" alt="License" /></a>
</p>

<p align="center">
  <a href="README.md">中文</a> |
  <a href="README_en.md">English</a> |
  <b>Tiếng Việt</b>
</p>

<p align="center">
  <b>Hệ thống tự động đăng ký và quản lý tài khoản đa nền tảng · 13+ nền tảng · 9+ dịch vụ email · Chế độ Protocol/Browser · Ứng dụng desktop một cú nhấp</b>
</p>

<a href="https://bestproxy.com/?keyword=l85nsbgw" target="_blank"><img src="assets/bestproxy.gif" alt="BestProxy - Residential IP độ tinh khiết cao, hỗ trợ chế độ một tài khoản một IP độc lập, chống liên kết toàn tuyến, tăng đáng kể tỷ lệ chấp nhận tài khoản và khả năng tồn tại lâu dài" width="100%"></a>

> ⚠️ **Tuyên bố miễn trừ**: Dự án này chỉ dành cho mục đích học tập và nghiên cứu, không được phép sử dụng cho bất kỳ mục đích thương mại nào. Người dùng tự chịu trách nhiệm về mọi hậu quả phát sinh khi sử dụng dự án này.

> 🌟 **Đây là upstream chính thức của [`lxf746/any-auto-register`](https://github.com/lxf746/any-auto-register)** — repository gốc của tác giả ban đầu, nơi cập nhật mới nhất và sớm nhất. Các repository khác có cùng tên đều là bản fork.

Hệ thống tự động đăng ký và quản lý tài khoản đa nền tảng, hỗ trợ mở rộng dạng plugin, tích hợp Web UI.

<a href="https://legionproxy.io/?utm_source=github&utm_campaign=any-auto-register" target="_blank"><img src="assets/legionproxy.png" alt="LegionProxy — Residential proxy được thiết kế cho đăng ký tài khoản và automation, 74M+ residential IP thật, 195+ quốc gia, kết nối HTTP/3 tốc độ cao, từ $0.60/GB" width="100%"></a>

[LegionProxy — Residential proxy chuyên cho đăng ký tài khoản và automation · 74M+ residential IP thật · 195+ quốc gia · HTTP/3 · Từ $0.60/GB](https://legionproxy.io/?utm_source=github&utm_campaign=any-auto-register)

## Mục lục

- [Điểm nổi bật](#điểm-nổi-bật)
- [Tính năng](#tính-năng)
- [Ảnh chụp màn hình](#ảnh-chụp-màn-hình)
- [Công nghệ sử dụng](#công-nghệ-sử-dụng)
- [Tải ứng dụng Desktop](#tải-ứng-dụng-desktop)
- [Bắt đầu nhanh](#bắt-đầu-nhanh)
- [Triển khai Docker](#triển-khai-docker)
- [Dịch vụ Email](#dịch-vụ-email)
- [Dịch vụ Captcha](#dịch-vụ-captcha)
- [Proxy Pool](#proxy-pool)
- [Dịch vụ SMS](#dịch-vụ-sms)
- [Vòng đời tài khoản](#vòng-đời-tài-khoản)
- [Dashboard thống kê](#dashboard-thống-kê)
- [Tích hợp Any2API](#tích-hợp-any2api)
- [Phát triển plugin](#phát-triển-plugin)
- [Câu hỏi thường gặp](#câu-hỏi-thường-gặp)
- [Nhà tài trợ](#nhà-tài-trợ)
- [Cộng đồng](#cộng-đồng)
- [Star History](#star-history)
- [Giấy phép](#giấy-phép)

## Điểm nổi bật

Vì sao nên chọn any-auto-register thay vì các công cụ tương tự:

| Khả năng | any-auto-register | Công cụ khác |
|------|------|------|
| 🖥️ **Ứng dụng desktop một cú nhấp** | ✅ Electron client cho Mac / Windows, không cần CLI | ❌ Thường chỉ có CLI / Docker |
| 🧩 **Độ phủ nền tảng** | ✅ 13+ nền tảng sẵn sàng + Anything adapter tổng quát | Thường 1-3 nền tảng |
| 📨 **Dịch vụ email** | ✅ 9 dịch vụ (tự host + công cộng + DDG) | Thường 1-2 |
| ⚡ **Ba chế độ thực thi** | ✅ Pure protocol (không browser, nhanh nhất) / headless / headed | Thường chỉ browser |
| 🔁 **Vòng đời tài khoản** | ✅ Kiểm tra hợp lệ, tự refresh token, cảnh báo trial hết hạn | ❌ Đa số chỉ đăng ký |
| 📊 **Dashboard tỷ lệ thành công** | ✅ Thống kê theo nền tảng / proxy / ngày, tổng hợp lỗi | ❌ |
| 🔌 **Tích hợp Any2API** | ✅ Đăng ký xong dùng được ngay, tự động đẩy lên gateway | ❌ |
| 📦 **Kiến trúc plugin** | ✅ Platform / mailbox / captcha / SMS / proxy đều cắm rời | Thường hardcode |

> 💡 Kết hợp [`Any2API`](https://github.com/lxf746/any2api) gateway + `any-auto-register` cho phép thực hiện chuỗi đầy đủ: **đăng ký hàng loạt tài khoản → tự động đẩy lên gateway → dùng ngay như API tương thích OpenAI/Claude**.

## Tính năng

- **Đa nền tảng**: ChatGPT, Cursor, Kiro, Trae.ai, Tavily, Grok, Blink, Cerebras, OpenBlockLabs, Windsurf, kèm Anything adapter tổng quát cho plugin tùy chỉnh
- **Đa dịch vụ email**: MoeMail (tự host), Laoudo, DuckMail, Testmail, Cloudflare Worker tự host, Freemail, TempMail.lol, Temp-Mail Web, DuckDuckGo Email
- **Thực thi đa chế độ**: API protocol (không browser) / headless browser / headed browser (theo từng nền tảng)
- **Captcha**: YesCaptcha, 2Captcha, Solver cục bộ (Camoufox)
- **SMS**: SMS-Activate, HeroSMS (cho các nền tảng yêu cầu xác minh số điện thoại)
- **Proxy pool**: Static round-robin + dynamic API extract + rotating gateway, weight theo tỷ lệ thành công, tự động vô hiệu hóa proxy lỗi
- **Vòng đời tài khoản**: Kiểm tra hợp lệ định kỳ, tự refresh token, cảnh báo trial hết hạn
- **Dashboard tỷ lệ thành công**: Thống kê theo nền tảng, ngày, proxy; tổng hợp lỗi
- **Đăng ký đồng thời**: Có thể cấu hình mức độ song song
- **Log thời gian thực**: Đẩy log SSE về frontend ngay khi chạy
- **Xuất tài khoản**: JSON, CSV, CPA, Sub2API, Kiro-Go, Any2API
- **Đồng bộ Any2API**: Tự động đẩy tài khoản đã đăng ký lên gateway, dùng được ngay
- **Hành động theo nền tảng**: Tùy biến từng nền tảng (ví dụ: chuyển tài khoản Kiro, sinh link nâng cấp Trae Pro)

## Ảnh chụp màn hình

> 📸 *Ảnh chụp sẽ được cập nhật theo từng phiên bản. Để trải nghiệm đầy đủ, hãy thử [Tải Desktop](#tải-ứng-dụng-desktop).*

### Dashboard
![Dashboard](assets/screenshots/dashboard.png)

### Tác vụ đăng ký
![Tác vụ đăng ký](assets/screenshots/register-task.png)

### Cài đặt
![Cài đặt](assets/screenshots/settings.png)

### Quản lý tài khoản
![Quản lý tài khoản](assets/screenshots/accounts.png)

## Công nghệ sử dụng

| Tầng | Công nghệ |
|------|------|
| Backend | FastAPI + SQLite (SQLModel) |
| Frontend | React + TypeScript + Vite + TailwindCSS |
| HTTP | curl_cffi (giả lập browser fingerprint) |
| Browser automation | Playwright / Camoufox |

## Tải ứng dụng Desktop

> 🚀 **Một cú nhấp, không cần cấu hình**: Không muốn cài Python và Node.js? Tải client desktop về và nhấp đôi là dùng được.

| Nền tảng | Tải xuống |
|------|------|
| 🍎 macOS (Intel / Apple Silicon) | [Tải `.dmg` từ Releases](https://github.com/lxf746/any-auto-register/releases/latest) |
| 🪟 Windows | [Tải `.exe` từ Releases](https://github.com/lxf746/any-auto-register/releases/latest) |

Client desktop được đóng gói bằng Electron, đã bao gồm sẵn backend Python và frontend React — sử dụng ngay không cần cấu hình. Mỗi phiên bản mới (`v*` tag) sẽ được build và phát hành tự động trên [Releases](https://github.com/lxf746/any-auto-register/releases).

## Bắt đầu nhanh

### Yêu cầu hệ thống

- Python 3.11+
- Node.js 18+

### Cài đặt

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

### Cài đặt browser (tùy chọn, cần thiết cho chế độ headless / headed)

```bash
python3 -m playwright install chromium
python3 -m camoufox fetch
```

### Chạy

```bash
.venv/bin/python3 -m uvicorn main:app --port 8000
```

Mở `http://localhost:8000` trên trình duyệt.

## Triển khai Docker

```bash
docker compose up -d
```

Truy cập `http://localhost:8000`. Database được lưu vào `./data/`.

Với chế độ headed browser, có thể xem quá trình automation qua noVNC tại `http://localhost:6080`.

## Dịch vụ Email

Chọn một dịch vụ email để nhận mã xác minh. Tất cả provider được quản lý qua trang **Settings → Providers** trong Web UI:

- **MoeMail** (khuyến nghị): tự host trên Cloudflare bằng [cloudflare_temp_email](https://github.com/dreamhunter2333/cloudflare_temp_email)
- **Laoudo**: email custom domain ổn định
- **Cloudflare Worker tự host**: kiểm soát hoàn toàn, tự deploy
- **DuckMail / TempMail.lol / Temp-Mail Web**: dịch vụ email tạm thời công cộng
- **DuckDuckGo Email**: alias `@duck.com` qua DDG Email Protection (cần forward IMAP)
- **Freemail**: dựa trên Cloudflare Worker, hỗ trợ admin token + username/password
- **Testmail**: chế độ namespace của `testmail.app`, phù hợp cho tác vụ song song

Chi tiết các trường cấu hình có trong UI editor và trong [README tiếng Anh](README_en.md#mailbox-providers).

## Dịch vụ Captcha

| Dịch vụ | Ghi chú |
|------|------|
| YesCaptcha | Đăng ký tại [yescaptcha.com](https://yescaptcha.com) để lấy Client Key |
| 2Captcha | Đăng ký tại [2captcha.com](https://2captcha.com) để lấy API Key |
| Local Solver | Dùng Camoufox cục bộ, chạy `python3 -m camoufox fetch` trước |

## Proxy Pool

Hệ thống hỗ trợ cả static và dynamic proxy:

- **Static proxy**: quản lý qua trang Proxy; weight theo tỷ lệ thành công; tự vô hiệu hóa sau 5 lần thất bại liên tiếp
- **Dynamic proxy**: provider dạng API extraction hoặc rotating gateway (BrightData, Oxylabs, IPRoyal...); fallback về static pool khi thất bại

## Dịch vụ SMS

Cho các nền tảng yêu cầu xác minh số điện thoại (ví dụ: Cursor):

| Dịch vụ | Ghi chú |
|------|------|
| SMS-Activate | API key + quốc gia mặc định |
| HeroSMS | API key + service code, country ID, giá tối đa, chính sách reuse số |

## Vòng đời tài khoản

Lifecycle manager nền chạy tự động:

- **Kiểm tra hợp lệ** mỗi 6 giờ — đánh dấu tài khoản không còn hợp lệ
- **Refresh token** mỗi 12 giờ — tự refresh các token sắp hết hạn (hiện hỗ trợ ChatGPT)
- **Cảnh báo trial** — đánh dấu các tài khoản trial sắp hết hạn

Trigger thủ công:

- `POST /api/lifecycle/check` — kích hoạt kiểm tra hợp lệ
- `POST /api/lifecycle/refresh` — kích hoạt refresh token
- `POST /api/lifecycle/warn` — kích hoạt cảnh báo trial
- `GET /api/lifecycle/status` — xem trạng thái manager

## Dashboard thống kê

Truy vấn thống kê đăng ký qua API:

- `GET /api/stats/overview` — tổng quan toàn cục
- `GET /api/stats/by-platform` — tỷ lệ thành công theo nền tảng
- `GET /api/stats/by-day?days=30` — xu hướng theo ngày
- `GET /api/stats/by-proxy` — xếp hạng proxy theo tỷ lệ thành công
- `GET /api/stats/errors?days=7` — tổng hợp lỗi

## Tích hợp Any2API

Kết hợp với [Any2API](https://github.com/lxf746/any2api) — tài khoản sau khi đăng ký được tự động đẩy lên gateway, dùng ngay như API tương thích OpenAI/Claude.

Cấu hình trong Settings:

| Trường | Mô tả |
|------|------|
| `any2api_url` | URL của Any2API instance, ví dụ: `http://localhost:8099` |
| `any2api_password` | Mật khẩu admin của Any2API |

Đích đẩy theo nền tảng: Kiro → `kiroAccounts`, Grok → `grokTokens`, Cursor → `cursorConfig`, ChatGPT → `chatgptConfig`, Blink → `blinkConfig`, Windsurf → `windsurfAccounts`.

Nếu không cấu hình `any2api_url`, tích hợp này sẽ được bỏ qua một cách yên lặng.

## Phát triển plugin

Thêm một nền tảng mới:

1. Tạo `platforms/myplatform/` với `__init__.py` và `plugin.py`
2. Implement subclass của `BasePlatform` và decorate với `@register`
3. Khai báo capability (`supported_executors`, `supported_identity_modes`...)

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

Plugin sẽ được tự động load khi khởi động. Xem [README tiếng Anh](README_en.md#plugin-development) để biết chi tiết đầy đủ.

## Câu hỏi thường gặp

**Captcha liên tục thất bại?**
Kiểm tra xem captcha provider đã cấu hình đúng chưa. Trong chế độ protocol, ưu tiên YesCaptcha/2Captcha. Trong chế độ browser, Camoufox sẽ thử click Turnstile checkbox trước rồi fallback về remote solver. Nếu vẫn thất bại, hãy kiểm tra chất lượng IP proxy — IP rủi ro cao sẽ gặp challenge nghiêm ngặt hơn.

**Proxy bị chặn / tỷ lệ thành công thấp?**
Dùng residential proxy thay vì datacenter IP. Giảm số lượng song song. Kiểm tra thống kê từng proxy trong trang Proxy và vô hiệu hóa các proxy yếu. Mỗi nền tảng có độ nhạy IP khác nhau — có thể cân nhắc proxy pool riêng cho từng nền tảng.

**Cài đặt cho chế độ browser?**
```bash
python3 -m playwright install chromium
python3 -m camoufox fetch
```

**Solver khởi động timeout?**
Local Turnstile Solver cần Camoufox được cài đặt. Chạy `python3 -m camoufox fetch` trước, sau đó nhấp "Restart Solver" trong trang Settings. Hoặc bỏ qua local Solver hoàn toàn và dùng YesCaptcha / 2Captcha.

## Nhà tài trợ

Cảm ơn các nhà tài trợ sau đã hỗ trợ lâu dài cho any-auto-register. Nếu dịch vụ của bạn hướng tới đăng ký tài khoản, automation hoặc nhà phát triển AI, đừng ngần ngại liên hệ.

| Logo | Tên | Mô tả | Link |
| --- | --- | --- | --- |
| <a href="https://bestproxy.com/?keyword=l85nsbgw" target="_blank"><img src="assets/bestproxy.gif" alt="BestProxy" width="140" /></a> | **BestProxy** | Residential IP độ tinh khiết cao, hỗ trợ chế độ một tài khoản một IP độc lập, chống liên kết toàn tuyến, tăng đáng kể tỷ lệ chấp nhận và khả năng tồn tại lâu dài. | [bestproxy.com](https://bestproxy.com/?keyword=l85nsbgw) |
| <a href="https://legionproxy.io/?utm_source=github&utm_campaign=any-auto-register" target="_blank"><img src="assets/legionproxy.png" alt="LegionProxy" width="140" /></a> | **LegionProxy** | Residential proxy chuyên cho đăng ký tài khoản và automation, 74M+ residential IP thật, 195+ quốc gia, kết nối HTTP/3 tốc độ cao, từ $0.60/GB. | [legionproxy.io](https://legionproxy.io/?utm_source=github&utm_campaign=any-auto-register) |

## Cộng đồng

Tham gia nhóm người dùng để cập nhật thông tin, kinh nghiệm cấu hình và mẹo đăng ký:

### Nhóm QQ (khuyến nghị)

**Mã nhóm: `1081650009`**

<a href="assets/qq-group.png" target="_blank"><img src="assets/qq-group.png" alt="Mã QR nhóm QQ" width="220" /></a>

Quét mã QR phía trên hoặc tìm theo mã nhóm để tham gia.

Để báo bug và yêu cầu tính năng, vui lòng dùng [Issues](https://github.com/lxf746/any-auto-register/issues).

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=lxf746/any-auto-register&type=Date)](https://star-history.com/#lxf746/any-auto-register&Date)

## Giấy phép

Dự án này được cấp phép theo [AGPL-3.0](LICENSE). Học tập và nghiên cứu cá nhân được sử dụng tự do; sử dụng thương mại phải tuân thủ AGPL-3.0 (sản phẩm phái sinh phải open source).
