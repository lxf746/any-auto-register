# Any Auto Register

<p align="center">
  <a href="https://linux.do" target="_blank">
    <img src="https://img.shields.io/badge/LINUX-DO-FFB003?style=for-the-badge&logo=linux&logoColor=white" alt="LINUX DO" />
  </a>
</p>

> ⚠️ Tuyên bố miễn trừ trách nhiệm: Dự án này chỉ phục vụ mục đích học tập và nghiên cứu, không được sử dụng cho bất kỳ mục đích thương mại nào. Người sử dụng dự án này phải tự chịu hoàn toàn trách nhiệm về mọi hậu quả phát sinh.

Hệ thống quản lý và tự động đăng ký tài khoản đa nền tảng, hỗ trợ mở rộng dạng plugin, quản lý qua Web UI, đăng ký hàng loạt, đồng bộ trạng thái, và tự động khởi chạy Turnstile Solver cục bộ.

## Mục lục

- [Giới thiệu dự án](#giới-thiệu-dự-án)
- [Giao diện hiện tại & các nền tảng được hỗ trợ](#giao-diện-hiện-tại--các-nền-tảng-được-hỗ-trợ)
- [Tính năng](#tính-năng)
- [Sản phẩm tự vận hành](#sản-phẩm-tự-vận-hành)
- [Danh sách nhà tài trợ](#danh-sách-nhà-tài-trợ)
- [Xem trước giao diện](#xem-trước-giao-diện)
- [Công nghệ sử dụng](#công-nghệ-sử-dụng)
- [Yêu cầu môi trường](#yêu-cầu-môi-trường)
- [Tính năng chuyên biệt cho ChatGPT](#tính-năng-chuyên-biệt-cho-chatgpt)
- [Hỗ trợ dịch vụ email](#hỗ-trợ-dịch-vụ-email)
- [Bắt đầu nhanh](#bắt-đầu-nhanh)
- [Triển khai bằng Docker](#triển-khai-bằng-docker)
- [Plugin & phụ thuộc bên ngoài](#plugin--phụ-thuộc-bên-ngoài)
- [Xử lý sự cố thường gặp](#xử-lý-sự-cố-thường-gặp)
- [Cấu trúc dự án](#cấu-trúc-dự-án)
- [Hướng dẫn phát triển Electron](#hướng-dẫn-phát-triển-electron)
- [Nhóm thảo luận người dùng](#nhóm-thảo-luận-người-dùng)
- [Ủng hộ tác giả](#ủng-hộ-tác-giả)
- [Lịch sử Star](#lịch-sử-star)
- [Giấy phép](#giấy-phép)

## Giới thiệu dự án

Dự án này được phát triển lại từ [lxf746/any-auto-register](https://github.com/lxf746/any-auto-register.git).

## Giao diện hiện tại & các nền tảng được hỗ trợ

Theo mã nguồn frontend hiện tại, **các nền tảng hiển thị mặc định trong menu "Quản lý nền tảng"** bao gồm:

- ChatGPT
- Grok
- Kiro (AWS Builder ID)
- OpenBlockLabs
- Trae.ai

## Tính năng

- **Quản lý & đăng ký tài khoản đa nền tảng**: Danh sách tài khoản thống nhất, chi tiết, nhập/xuất, xóa, thao tác hàng loạt
- **Nhiều chế độ thực thi**: Giao thức thuần, trình duyệt không giao diện (headless), trình duyệt có giao diện (headed)
- **Tích hợp nhiều dịch vụ email**: Tích hợp sẵn, bên thứ 3,自建 Worker Email và nhiều giải pháp khác
- **Hỗ trợ Captcha**: YesCaptcha, Turnstile Solver cục bộ (Camoufox)
- **Hỗ trợ Proxy**: Luân phiên pool proxy, duy trì trạng thái proxy, tích hợp proxy trong quá trình đăng ký
- **Đăng ký hàng loạt**: Hỗ trợ cài đặt số lượng đăng ký, số lượng đồng thời, độ trễ khởi động giữa mỗi tài khoản
- **Log thời gian thực**: Xem log đăng ký trực tiếp trên frontend
- **Quản lý lịch sử tác vụ**: Xem lịch sử và xóa hàng loạt
- **Mở rộng dạng plugin**: Có thể tích hợp dịch vụ bên ngoài và quản lý độc lập

## Sản phẩm tự vận hành

Cảm ơn những sản phẩm tự vận hành đã hỗ trợ any-auto-register.

| Logo | Tên | Giới thiệu | Website |
| --- | --- | --- | --- |
| <a href="https://faka.gsyun.cloud/" target="_blank"><img src="frontend/public/logo.png" alt="阿晨小铺" width="140" /></a> | 阿晨小铺 | 本人经营,诚信稳定 | [https://faka.gsyun.cloud/](https://faka.gsyun.cloud/) |
| <a href="https://api.codelife.eu.cc/" target="_blank">zc-api</a> | zc-api | Dịch vụ trung chuyển cho các tình huống gọi mô hình như Claude Code và Codex. Băng thông 10Gbps đảm bảo phản hồi token đầu tiên nhanh hơn và kết nối ổn định. Cung cấp giao diện tin cậy cao, tích hợp dễ dàng và hỗ trợ giao hàng liên tục, phù hợp cho nhà phát triển và nhóm sử dụng lâu dài. Có hỗ trợ hóa đơn; truy cập trang chính thức để biết chi tiết. | [https://api.codelife.eu.cc/](https://api.codelife.eu.cc/) |

## Danh sách nhà tài trợ

Cảm ơn những người bạn và đối tác đã hỗ trợ any-auto-register.

| Logo | Tên | Giới thiệu | Website |
| --- | --- | --- | --- |
| <a href="https://www.rapidproxy.io/?code=IFZZROPF1" target="_blank"><img src="frontend/public/RapidProxy.png" alt="RapidProxy" width="140" /></a> | RapidProxy | RapidProxy cung cấp hỗ trợ proxy ổn định cho các tình huống đăng ký tự động và quản lý tài khoản.<br><br>RapidProxy cung cấp mạng IP dân cư toàn cầu, hỗ trợ xoay vòng thông minh, phiên ổn định và yêu cầu đồng thời cao, giúp nhà phát triển hoàn thành tác vụ hàng loạt hiệu quả hơn và tối ưu môi trường thực thi tự động.<br><br>Proxy dân cư động chỉ từ $0.55/GB, lưu lượng có hiệu lực dài hạn không hết hạn.<br><br>**Tình huống sử dụng:**<br>Đăng ký tự động / Tự động hóa trình duyệt (Playwright, Selenium) / Quản lý môi trường nhiều tài khoản / Tác vụ thu thập dữ liệu<br><br>Đăng ký để nhận 500MB dùng thử miễn phí; mời bạn bè để kiếm lên đến 15% hoa hồng!<br><br>**Mã giảm giá độc quyền: RAPID10 (giảm 10%)** | [https://www.rapidproxy.io/?code=IFZZROPF1](https://www.rapidproxy.io/?code=IFZZROPF1) |

## Xem trước giao diện

### Bảng điều khiển

![Bảng điều khiển](docs/images/dashboard.png)

### Cấu hình toàn cục / Quản lý plugin

![Cấu hình toàn cục / Quản lý plugin](docs/images/settings-integrations.png)

## Công nghệ sử dụng

| Tầng | Công nghệ |
| --- | --- |
| Backend | FastAPI + SQLite (SQLModel) |
| Frontend | React + TypeScript + Vite |
| HTTP | curl_cffi |
| Tự động hóa trình duyệt | Playwright / Camoufox |

## Yêu cầu môi trường

- Python 3.12+
- Node.js 18+
- Conda (khuyến nghị)
- Windows (khuyến nghị sử dụng script khởi động có sẵn trong repo)

## Tính năng chuyên biệt cho ChatGPT

Trong phiên bản hiện tại, **ChatGPT là một trong những nền tảng có chức năng hoàn thiện nhất**, không chỉ hỗ trợ đăng ký mà còn quản lý vòng đời Token, dò trạng thái và đồng bộ hệ thống bên ngoài.

### 1. Chuyển đổi phương thức Token ChatGPT

Phiên bản hiện tại cung cấp hai chế độ đăng ký ChatGPT:

- **Có RT** (khuyến nghị mặc định)
  - Đi theo đường dẫn PR mới
  - Xuất ra **Access Token + Refresh Token**
- **Không có RT** (tương thích phương thức cũ)
  - Đi theo đường dẫn cũ
  - Chỉ xuất ra **Access Token / Session**
  - Các chức năng phụ thuộc RT có thể không hoạt động

Chuyển đổi này có thể tìm thấy ở:

- Trang tác vụ đăng ký
- Cửa sổ popup đăng ký ChatGPT

### 4. Đồng bộ trạng thái hàng loạt & re-upload cho ChatGPT

Ở đầu trang danh sách ChatGPT, hiện có hai loại chức năng hàng loạt:

- **Đồng bộ trạng thái**
  - Đồng bộ trạng thái tài khoản cục bộ đã chọn
  - Đồng bộ trạng thái CLIProxyAPI đã chọn
  - Hoặc thực hiện hàng loạt theo bộ lọc hiện tại
- **Re-upload những tài khoản không tìm thấy ở remote**
  - Re-upload auth-file không tìm thấy ở remote
  - Hỗ trợ "phạm vi lọc hiện tại" hoặc "tài khoản đã chọn hiện tại"

## Hỗ trợ dịch vụ email

Theo cấu hình thực tế trong trang đăng ký, dự án hỗ trợ các dịch vụ email sau:

| Tên dịch vụ | Định danh | Ghi chú |
| --- | --- | --- |
| LuckMail | `luckmail` | Có thể đăng ký miễn phí để test, **check-in hàng ngày để tiếp tục nhận email** |
| MoeMail | `moemail` | Phương án mặc định phổ biến, tự động đăng ký tài khoản và tạo email |
| TempMail.lol | `tempmail_lol` | Email tạm thời, một số khu vực có thể cần proxy |
| SkyMail (CloudMail) | `skymail` | Sử dụng qua API / Token / Domain |
| YYDS Mail / MaliAPI | `maliapi` | Hỗ trợ chiến lược domain tự động |
| GPTMail | `gptmail` | Tạo email tạm thời qua GPTMail API và xoay vòng, hỗ trợ ghép ngẫu nhiên khi đã biết domain |
| DuckMail | `duckmail` | Email tạm thời |
| Freemail | `freemail` | Dịch vụ email tự xây dựng |
| Laoudo | `laoudo` | Email cố định |
| CF Worker | `cfworker` |自建 email qua Cloudflare Worker |

### Ghi chú về email cho Kiro

Kiro hiện có kiểm soát rủi ro khá nghiêm ngặt, phương án email sẽ ảnh hưởng đáng kể đến tỉ lệ thành công. Dự án cũng đã lưu lại lưu ý này:

- **Email tự xây dựng: tỉ lệ thành công 100%**
- **Email tạm thời tích hợp sẵn trong dự án: tỉ lệ thành công 0%**

Do đó khi đăng ký **Kiro (AWS Builder ID)**, khuyến nghị ưu tiên sử dụng **email tự xây dựng**.

## Bắt đầu nhanh

### 1. Tạo và kích hoạt môi trường Conda

```bash
conda create -n any-auto-register python=3.12 -y
conda activate any-auto-register
```

### 2. Cài đặt phụ thuộc backend

```bash
pip install -r requirements.txt
```

### 3. Cài đặt phụ thuộc trình duyệt

```bash
python -m playwright install chromium
python -m camoufox fetch
```

### 4. Cài đặt và build frontend

```bash
cd frontend
npm install
npm run build
cd ..
```

Sau khi build xong, tài nguyên tĩnh được xuất ra:

```text
./static
```

### 5. Khởi động dự án

#### Khuyến nghị cho Windows

PowerShell:

```powershell
.\start_backend.ps1
```

CMD:

```bat
start_backend.bat
```

#### Khởi động thủ công

```bash
conda activate any-auto-register
python main.py
```

Sau khi khởi động, truy cập mặc định:

```text
http://localhost:8000
```

> Nếu đã thực hiện `npm run build`, frontend sẽ do FastAPI trực tiếp quản lý, do đó truy cập qua `8000`, không phải `5173`.

## Script khởi động Windows

Repo đã cung cấp các script sau:

- `start_backend.bat`
- `start_backend.ps1`
- `stop_backend.bat`
- `stop_backend.ps1`

Các script này bắt buộc sử dụng môi trường `any-auto-register` để khởi động/dừng backend, tránh các vấn đề thường gặp:

- Backend khởi động được nhưng Solver không chạy
- `ModuleNotFoundError: quart`
- Turnstile Solver trên frontend luôn hiển thị "Chưa chạy"

Khi dừng dịch vụ, thực thi:

PowerShell:

```powershell
.\stop_backend.ps1
```

CMD:

```bat
stop_backend.bat
```

Mặc định sẽ dừng:

- Cổng backend: `8000`
- Cổng Solver: `8889`

## Chế độ phát triển Frontend

Phù hợp khi cần debug giao diện React.

### Terminal 1: Khởi động backend

```powershell
.\start_backend.ps1
```

### Terminal 2: Khởi động Vite

```bash
cd frontend
npm run dev
```

Truy cập:

```text
http://localhost:5173
```

Vite sẽ proxy các request `/api` về backend `http://localhost:8000`.

## Giải thích về Turnstile Solver

### Tự động khởi động

Turnstile Solver cục bộ sẽ tự động chạy khi FastAPI backend khởi động, mặc định tại:

```text
http://localhost:8889
```

Frontend "Cấu hình toàn cục → Captcha → Turnstile Solver" hiển thị **kết quả dò từ backend**, do đó:

- Backend chưa khởi động → Frontend hiển thị "Chưa chạy"
- Backend đã khởi động nhưng không đúng môi trường conda → Solver có thể không khởi động được

### Khởi động Solver thủ công

```bash
conda activate any-auto-register
python services/turnstile_solver/start.py --browser_type camoufox --port 8889
```

### Log Solver

Nếu khởi động thất bại, xem:

```text
services/turnstile_solver/solver.log
```

## Triển khai bằng Docker

Thư mục gốc repo đã cung cấp:

- `Dockerfile`
- `docker-compose.yml`

Nội dung triển khai mặc định bao gồm:

- FastAPI Backend
- Tài nguyên tĩnh frontend đã build
- Persist thư mục database SQLite `./data`
- Turnstile Solver tự động khởi chạy kèm backend

### Khởi động

```bash
docker compose up -d --build
```

Lần build đầu tiên sẽ tải thêm phụ thuộc Python, Playwright Chromium và Camoufox, do đó thời gian sẽ lâu hơn đáng kể.

Dockerfile hiện tại đã được sửa để cài Camoufox qua link trực tiếp, tránh giới hạn ẩn danh khi truy cập GitHub Releases API.

### Truy cập

```text
http://localhost:8000
```

### Dừng

```bash
docker compose down
```

### Xem log

```bash
docker compose logs -f app
```

### Persist dữ liệu

Container mặc định sử dụng:

```text
DATABASE_URL=sqlite:////app/data/account_manager.db
```

Host machine sẽ mount vào:

```text
./data
```

### Biến môi trường thường dùng

| Biến | Mặc định | Ghi chú |
| --- | --- | --- |
| `HOST` | `0.0.0.0` | Địa chỉ lắng nghe FastAPI |
| `PORT` | `8000` | Cổng lắng nghe FastAPI |
| `DATABASE_URL` | `sqlite:////app/data/account_manager.db` | Đường dẫn database SQLite |
| `APP_ENABLE_SOLVER` | `1` | Có tự động khởi chạy Solver không, đặt `0` để tắt |
| `SOLVER_PORT` | `8889` | Cổng lắng nghe Solver |
| `LOCAL_SOLVER_URL` | `http://127.0.0.1:8889` | Địa chỉ backend truy cập Solver |

Nếu cần thay đổi cấu hình như `SMSTOME_COOKIE`, `OPENAI_*`, chỉ cần ghi vào file `.env` ở thư mục gốc repo, `docker compose` sẽ tự động inject vào môi trường container.

### Tham số build Camoufox

Nếu cần ghi đè phiên bản upstream, có thể chỉ định khi build:

```bash
CAMOUFOX_VERSION=135.0.1 CAMOUFOX_RELEASE=beta.24 docker compose build app
```

### Khuyến nghị sử dụng Docker

- Image hiện tại chủ yếu bao phủ ứng dụng chính và Turnstile Solver cục bộ
- Logic tự động cài đặt/khởi chạy `grok2api`, `CLIProxyAPI`, `Kiro Account Manager` vẫn thiên về môi trường host machine
- Nếu phụ thuộc vào `conda`, Go hoặc file thực thi Windows, không khuyến nghị chạy trực tiếp trong Linux container hiện tại
- Nếu chỉ cần Web UI, quản lý tài khoản, điều phối tác vụ và Solver cục bộ, cấu hình Compose hiện tại có thể sử dụng trực tiếp

## Plugin & phụ thuộc bên ngoài

### Nguồn email tạm thời

Dự án hỗ trợ自建 email tạm thời qua Cloudflare Worker, nguồn giải pháp từ:

- <https://github.com/dreamhunter2333/cloudflare_temp_email>

### Địa chỉ Git plugin bên ngoài

Dự án hiện hỗ trợ cài đặt/khởi động các thành phần bên ngoài sau:

| Dự án | Mục đích | Địa chỉ Git |
| --- | --- | --- |
| CLIProxyAPI | Dịch vụ quản lý CPA / Proxy Pool | `https://github.com/router-for-me/CLIProxyAPI.git` |
| grok2api | Quản lý token Grok, điền ngược, dịch vụ chat/API | `https://github.com/chenyme/grok2api.git` |
| kiro-account-manager | Plugin quản lý tài khoản Kiro | `https://github.com/hj01857655/kiro-account-manager.git` |

Nút **"Cài đặt phiên bản mới nhất / Cập nhật lên phiên bản mới nhất"** trong trang plugin sẽ đồng bộ code mới nhất từ repo, và đã hỗ trợ **gỡ cài đặt** (sẽ dừng dịch vụ trước, sau đó xóa thư mục plugin cục bộ).
Mặc định cập nhật theo **semver tag mới nhất**; cũng có thể chuyển về chế độ **branch HEAD** trong "Cài đặt → Plugin → Chiến lược cài đặt/cập nhật".

Nếu cần thay đổi địa chỉ `ghproxy`, `gitclone`, mirror Git doanh nghiệp hoặc proxy khác, cần đồng bộ sửa đổi:

```text
services/external_apps.py
```

## Xử lý sự cố thường gặp

### 1. Turnstile Solver hiển thị "Chưa chạy" trên frontend

Trước tiên kiểm tra backend đã khởi động chưa:

```bash
curl http://localhost:8000/api/solver/status
```

Kết quả trả về bình thường:

```json
{"running":true}
```

Nếu không truy cập được cổng `8000`, vấn đề nằm ở backend, không phải Solver.

### 2. Lỗi `ModuleNotFoundError: quart`

Python khởi động backend hiện tại không phải môi trường `any-auto-register`, vui lòng sử dụng:

```powershell
.\start_backend.ps1
```

hoặc:

```bat
start_backend.bat
```

### 3. Xác nhận Python hiện tại có chính xác không

```bash
python -c "import sys; print(sys.executable)"
```

Kết quả mong đợi:

```text
D:\miniconda\conda3\envs\any-auto-register\python.exe
```

### 4. Solver mở được nhưng trạng thái vẫn bất thường

Kiểm tra hai địa chỉ sau:

```text
http://localhost:8000/api/solver/status
http://localhost:8889/
```

Nếu địa chỉ thứ hai mở được nhưng địa chỉ thứ nhất không thông, vấn đề nằm ở backend, không phải Solver.

### 5. Cổng bị chiếm dụng

Nếu khởi động báo lỗi `WinError 10048`, trước tiên thực thi:

```powershell
.\stop_backend.ps1
```

Sau đó khởi động lại:

```powershell
.\start_backend.ps1
```

## Cấu trúc dự án

```text
any-auto-register/
├── api/
├── core/
├── docs/
├── electron/
├── frontend/
├── platforms/
├── services/
│   ├── solver_manager.py
│   └── turnstile_solver/
├── static/
├── tests/
├── main.py
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
├── start_backend.bat
├── start_backend.ps1
├── stop_backend.bat
└── stop_backend.ps1
```

## Hướng dẫn phát triển Electron

Chế độ phát triển Electron sẽ không tự động khởi động Python backend.

Vui lòng khởi động backend tại thư mục gốc dự án trước:

```powershell
.\start_backend.ps1
```

Sau đó mới chạy Electron.

## Nhóm thảo luận người dùng

- Nhóm QQ: **1065114376** (Nhóm thảo luận người dùng đăng ký any-auto-register)

## Ủng hộ tác giả

Nếu dự án này hữu ích với bạn, vui lòng ủng hộ để tác giả tiếp tục duy trì và cập nhật dự án.

![Mã ủng hộ](docs/images/dashang.JPG)

## Lịch sử Star

<a href="https://star-history.dera.page/#zc-zhangchen/any-auto-register&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://star-history.dera.page/svg?repos=zc-zhangchen/any-auto-register&type=date&theme=dark&legend=top-left" />
   <source media="(prefers-color-scheme: light)" srcset="https://star-history.dera.page/svg?repos=zc-zhangchen/any-auto-register&type=date&legend=top-left" />
   <img alt="Star History Chart" src="https://star-history.dera.page/svg?repos=zc-zhangchen/any-auto-register&type=date&legend=top-left" />
 </picture>
</a>

## Giấy phép

Giấy phép MIT — Chỉ phục vụ mục đích học tập và nghiên cứu, nghiêm cấm sử dụng cho mục đích thương mại.
