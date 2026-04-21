# Any Auto Register

<a href="https://bestproxy.com/?keyword=l85nsbgw" target="_blank"><img src="assets/bestproxy.gif" alt="BestProxy - 高纯度住宅IP资源，支持一号一IP独享模式，全链路防关联，显著提升账号通过率与长期存活率" width="100%"></a>

> ⚠️ **免责声明**：本项目仅供学习和研究使用，不得用于任何商业用途。使用本项目所产生的一切后果由使用者自行承担。

多平台账号自动注册与管理系统，支持插件化扩展，内置 Web UI。

## 功能特性

- **多平台支持**：ChatGPT、Cursor、Kiro、Trae.ai、Tavily、Grok、Blink、Cerebras、OpenBlockLabs，支持自定义插件扩展（Anything 通用适配器）
- **多邮箱服务**：MoeMail（自建）、Laoudo、DuckMail、Testmail、Cloudflare Worker 自建邮箱、Freemail、TempMail.lol、Temp-Mail Web
- **多执行模式**：API 协议（无浏览器）、无头浏览器、有头浏览器（各平台按需支持）
- **验证码服务**：YesCaptcha、2Captcha、本地 Solver（Camoufox）
- **接码服务**：SMS-Activate（支持全球手机号租用，用于需要手机验证的平台）
- **代理池管理**：静态代理轮询 + 动态代理 API 提取 + 旋转网关代理，成功率统计、自动禁用失效代理
- **账号生命周期**：定时有效性检测、token 自动续期、trial 过期预警
- **注册成功率仪表盘**：按平台、按天、按代理的成功率统计，错误聚合分析
- **并发注册**：可配置并发数
- **实时日志**：SSE 实时推送注册日志到前端
- **账号导出**：支持 JSON、CSV、CPA、Sub2API、Kiro-Go、Any2API 多种格式
- **Any2API 联动**：注册完成后自动推送账号到 Any2API 网关，注册即可用
- **平台扩展操作**：各平台可自定义操作（如 Kiro 账号切换、Trae Pro 升级链接生成）

<a href="https://legionproxy.io/?utm_source=github&utm_campaign=any-auto-register" target="_blank"><img src="assets/legionproxy.png" alt="LegionProxy—住宅代理专为账号注册与自动化打造，74M+ 真实住宅IP，195+ 国家，HTTP/3 高速连接，$0.60/GB 起" width="100%"></a>

[LegionProxy—住宅代理专为账号注册与自动化打造 74M+ 真实住宅IP · 195+ 国家 · HTTP/3 高速连接 · $0.60/GB 起](https://legionproxy.io/?utm_source=github&utm_campaign=any-auto-register)

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI + SQLite（SQLModel）|
| 前端 | React + TypeScript + Vite + TailwindCSS |
| HTTP | curl_cffi（浏览器指纹伪装）|
| 浏览器自动化 | Playwright / Camoufox |

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+

### 安装

#### macOS / Linux

```bash
# 克隆项目
git clone <repo_url>
cd account_manager

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装后端依赖
pip install -r requirements.txt

# 构建前端
cd frontend
npm install
npm run build
cd ..
```

#### Windows

```bat
:: 克隆项目
git clone <repo_url>
cd account_manager

:: 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate

:: 安装后端依赖
pip install -r requirements.txt

:: 构建前端
cd frontend
npm install
npm run build
cd ..
```

### 安装浏览器（可选，无头/有头浏览器模式需要）

```bash
# Playwright 浏览器
python3 -m playwright install chromium

# Camoufox（用于本地 Turnstile Solver）
python3 -m camoufox fetch
```

### 启动

#### macOS / Linux

```bash
.venv/bin/python3 -m uvicorn main:app --port 8000
```

#### Windows

```bat
.venv\Scripts\python -m uvicorn main:app --port 8000
```

浏览器访问 `http://localhost:8000`

说明：

- 启动入口统一为 `main:app`
- 后端接口统一位于 `/api/*`
- 生产模式下前端构建产物由后端直接托管，访问 `http://localhost:8000` 即可
- 开发模式下前端独立运行在 `http://localhost:5173`，通过 Vite 代理转发 API 请求
- 前后端接口文档见 [docs/frontend-api-contract.md](docs/frontend-api-contract.md)
- 新的 C 端 / 管理端独立 API 项目见 [customer_portal_api/README.md](customer_portal_api/README.md)

### 开发模式（前端热更新）

```bash
cd frontend
npm run dev
# 访问 http://localhost:5173
```

### Docker 部署

一键启动：

```bash
docker compose up -d
```

访问 `http://localhost:8000`。数据库自动持久化到 `./data/` 目录。

如需使用有头浏览器模式（headed），可通过 noVNC 在浏览器中查看自动化过程：`http://localhost:6080`。

自定义配置：

```yaml
# docker-compose.yml
services:
  app:
    environment:
      - VNC_PASSWORD=your_password  # 设置 VNC 密码（可选）
```

重新构建（代码更新后）：

```bash
docker compose up -d --build
```

## 邮箱服务配置

注册时需要选择一种邮箱服务用于接收验证码。当前版本的邮箱和验证码配置都由后端 provider catalog 驱动，前端“全局配置”页已经改成列表式 CRUD：

- 左侧显示已添加的 provider 配置
- 右侧统一编辑名称、认证方式和字段
- “新增 Provider”下拉框只展示后端当前已接入但尚未加入的 provider
- 后端新增 provider 后，前端无需写死选项，刷新页面即可出现

目前数据库模型仍是 `provider_type + provider_key` 唯一，也就是每种 provider 保留一条配置；这套结构适合持续扩展新的 mailbox/captcha provider。

### MoeMail（推荐）

基于开源项目 [cloudflare_temp_email](https://github.com/dreamhunter2333/cloudflare_temp_email) 自建的临时邮箱服务，无需配置任何参数，系统自动注册临时账号并生成邮箱。

在注册页选择 **MoeMail**，填写你部署的实例地址（默认使用公共实例）。

### Laoudo

使用固定的自有域名邮箱，稳定性最高，适合长期使用。

| 参数 | 说明 |
|------|------|
| 邮箱地址 | 完整邮箱地址，如 `user@example.com` |
| Account ID | 邮箱账号 ID（在 Laoudo 面板查看）|
| JWT Token | 登录后从浏览器 Cookie 或接口获取的认证 Token |

### Cloudflare Worker 自建邮箱

基于 [cloudflare_temp_email](https://github.com/dreamhunter2333/cloudflare_temp_email) 自行部署的邮箱服务，完全自主可控。

**部署步骤**：参考项目文档，部署 Cloudflare Worker + D1 数据库 + Email Routing。

| 参数 | 说明 |
|------|------|
| API URL | Worker 的后端 API 地址，如 `https://api.your-domain.com` |
| Admin Token | 管理员密码，在 Worker 环境变量 `ADMIN_PASSWORDS` 中配置 |
| 域名 | 收件邮箱的域名，如 `your-domain.com`（需配置 MX 记录指向 Cloudflare）|
| Fingerprint | 可选，Worker 开启 fingerprint 验证时填写 |

### DuckMail

公共临时邮箱服务，无需配置，直接使用。部分地区需要代理。

### TempMail.lol

公共临时邮箱服务，无需配置，自动生成匿名邮箱。

### Temp-Mail Web

基于 web2.temp-mail.org 的临时邮箱服务，无需配置。

### Freemail

基于 Cloudflare Worker 自建的邮箱服务，支持管理员令牌和用户名密码两种认证方式。

| 参数 | 说明 |
|------|------|
| API URL | Freemail 服务地址 |
| 管理员令牌 | 管理员认证令牌 |
| 用户名 | 可选，用户名密码认证 |
| 密码 | 可选，用户名密码认证 |

### Testmail

`testmail.app` 的 namespace 邮箱模式。系统会自动生成地址：

- `{namespace}.{随机tag}@inbox.testmail.app`

适合并发任务，因为每次注册都会分配新的 tag，并在查询时自动带上 `tag + timestamp_from` 过滤旧邮件。

| 参数 | 说明 |
|------|------|
| API URL | 默认 `https://api.testmail.app/api/json` |
| Namespace | 你的 namespace，例如 `3xw8n` |
| Tag Prefix | 可选，给随机 tag 增加前缀，便于分类 |
| API Key | testmail.app 控制台里的 API Key |

## 验证码服务配置

| 服务 | 说明 |
|------|------|
| YesCaptcha | 需填写 Client Key，在 [yescaptcha.com](https://yescaptcha.com) 注册获取 |
| 2Captcha | 需填写 API Key，在 [2captcha.com](https://2captcha.com) 注册获取 |
| 本地 Solver | 使用 Camoufox 本地解码，需先执行 `python3 -m camoufox fetch` |

## 代理池配置

系统支持两种代理模式，可同时使用：

### 静态代理

在代理管理页手动添加固定代理地址，系统按成功率加权轮询。连续失败 5 次的代理自动禁用。

### 动态代理（API 提取）

在全局配置页添加 proxy provider，系统每次注册时自动从 API 获取新代理：

| Provider | 说明 |
|----------|------|
| API 提取代理 | 通过 HTTP API 动态提取代理 IP，适用于大多数代理商的 API 提取接口 |
| 旋转网关代理 | 固定入口地址，每次请求自动分配不同出口 IP，适用于 BrightData、Oxylabs、IPRoyal 等 |

动态代理优先于静态代理。未配置动态代理时自动回退到静态代理池。

## 接码服务配置

部分平台注册需要手机号验证（如 Cursor），可配置接码服务自动完成：

| 服务 | 说明 |
|------|------|
| SMS-Activate | 需填写 API Key，在 [sms-activate.guru](https://sms-activate.guru) 注册获取，支持全球手机号 |

## 账号生命周期管理

系统内置后台生命周期管理器，自动执行以下任务：

- **有效性检测**：每 6 小时自动检测活跃账号是否仍然有效，失效账号标记为 invalid
- **Token 自动续期**：每 12 小时自动刷新即将过期的 token（当前支持 ChatGPT）
- **Trial 过期预警**：扫描 trial 账号，即将过期的标记预警，已过期的自动更新状态

也可通过 API 手动触发：

- `POST /api/lifecycle/check` — 手动触发有效性检测
- `POST /api/lifecycle/refresh` — 手动触发 token 刷新
- `POST /api/lifecycle/warn` — 手动触发过期预警
- `GET /api/lifecycle/status` — 查看生命周期管理器状态

## 注册成功率仪表盘

通过 API 查询注册统计数据，用于监控和优化注册流程：

- `GET /api/stats/overview` — 全局概览（总注册数、成功率、账号状态分布）
- `GET /api/stats/by-platform` — 按平台统计成功率
- `GET /api/stats/by-day?days=30` — 按天统计注册趋势
- `GET /api/stats/by-proxy` — 代理成功率排行
- `GET /api/stats/errors?days=7` — 失败错误聚合

## Any2API 联动

配合 [Any2API](https://github.com/lxf746/any2api) 项目使用，注册完成后自动推送账号到 Any2API 网关，实现注册即可用。

### 配置方法

在全局配置中设置：

| 参数 | 说明 |
|------|------|
| `any2api_url` | Any2API 实例地址，如 `http://localhost:8099` |
| `any2api_password` | Any2API 管理密码 |

配置后，每次注册成功会自动将账号推送到 Any2API 对应的 provider：

| 平台 | 推送目标 |
|------|----------|
| Kiro | `kiroAccounts` 账号池 |
| Grok | `grokTokens` token 池 |
| Cursor | `cursorConfig` cookie |
| ChatGPT | `chatgptConfig` token |
| Blink | `blinkConfig` 凭证 |

未配置 `any2api_url` 时此功能静默跳过，不影响正常注册。

### 手动导出

也可以手动导出账号到 Any2API 或 Kiro-Go 格式：

- `POST /api/accounts/export/any2api` — 导出为 Any2API admin.json 格式（支持多平台混合导出）
- `POST /api/accounts/export/kiro-go` — 导出为 Kiro-Go config.json 格式

## 项目结构

```
account_manager/
├── main.py                 # FastAPI 入口
├── Dockerfile              # Docker 构建
├── docker-compose.yml      # Docker Compose 编排
├── requirements.txt        # Python 依赖
├── api/                    # HTTP 路由层
│   ├── accounts.py         # 账号 CRUD + 导出
│   ├── account_checks.py   # 账号检测
│   ├── lifecycle.py        # 生命周期管理
│   ├── stats.py            # 注册成功率仪表盘
│   ├── task_commands.py    # 注册任务创建 + SSE
│   ├── tasks.py            # 任务查询
│   ├── task_logs.py        # 历史任务日志
│   ├── actions.py          # 平台操作
│   ├── config.py           # 配置读写
│   ├── platforms.py        # 平台列表
│   ├── platform_capabilities.py
│   ├── provider_definitions.py  # Provider 定义管理
│   ├── provider_settings.py     # Provider 配置管理
│   ├── proxies.py          # 代理管理
│   ├── health.py           # 健康检查
│   └── system.py           # Solver 管理
├── application/            # 应用服务层
├── domain/                 # 领域模型
├── infrastructure/         # 仓储与运行时适配
├── core/                   # 基础能力
│   ├── base_platform.py    # 平台基类
│   ├── base_mailbox.py     # 邮箱服务基类 + 工厂方法
│   ├── base_captcha.py     # 验证码服务基类
│   ├── base_sms.py         # 接码服务基类 + SMS-Activate
│   ├── base_identity.py    # 身份提供者基类
│   ├── registration/       # 注册流程编排（适配器 + 流程）
│   ├── lifecycle.py        # 账号生命周期管理
│   ├── proxy_providers.py  # 动态代理提供者
│   ├── any2api_sync.py     # Any2API 自动推送
│   ├── db.py               # 数据模型
│   ├── proxy_pool.py       # 代理池（静态 + 动态）
│   ├── registry.py         # 平台插件注册表
│   ├── scheduler.py        # 定时任务
│   └── oauth_browser.py    # OAuth 浏览器基类
├── platforms/              # 平台插件层
│   └── {platform}/
│       ├── plugin.py           # 平台适配层
│       ├── protocol_mailbox.py # 协议模式注册
│       ├── browser_register.py # 浏览器注册（按需）
│       ├── browser_oauth.py    # 浏览器 OAuth（按需）
│       ├── core.py             # 平台协议核心逻辑（按需）
│       └── switch.py           # 账号切换逻辑（按需）
├── resources/              # 静态配置
│   ├── platform_capabilities.json
│   └── provider_driver_templates.json
├── services/               # 后台服务
│   ├── solver_manager.py   # Turnstile Solver 进程管理
│   └── task_runtime.py     # 持久化任务执行器
├── customer_portal_api/    # C 端 / 管理端独立 API
├── electron/               # Electron 桌面端打包
├── scripts/
│   └── smoke.py            # API 冒烟检查
├── tests/                  # 测试
└── frontend/               # React 前端
```

## 插件开发

添加新平台需要以下步骤：

### 1. 新建平台目录

在 `platforms/` 下新建目录，必须包含 `__init__.py` 和 `plugin.py`（`pkgutil.iter_modules` 只扫描带 `__init__.py` 的 Python 包）：

```
platforms/myplatform/
├── __init__.py
├── plugin.py              # 平台适配层（必须）
├── protocol_mailbox.py    # 协议模式注册逻辑（按需）
├── browser_register.py    # 浏览器注册逻辑（按需）
└── browser_oauth.py       # 浏览器 OAuth 逻辑（按需）
```

### 2. 实现 plugin.py

```python
from core.base_platform import BasePlatform, Account, AccountStatus, RegisterConfig
from core.base_mailbox import BaseMailbox
from core.registration import ProtocolMailboxAdapter, OtpSpec, RegistrationResult
from core.registry import register


@register
class MyPlatform(BasePlatform):
    name = "myplatform"
    display_name = "My Platform"
    version = "1.0.0"

    def __init__(self, config: RegisterConfig = None, mailbox: BaseMailbox = None):
        super().__init__(config)
        self.mailbox = mailbox

    def build_protocol_mailbox_adapter(self):
        """协议模式注册适配器"""
        return ProtocolMailboxAdapter(
            result_mapper=lambda ctx, result: RegistrationResult(
                email=result["email"],
                password=result.get("password", ""),
                status=AccountStatus.REGISTERED,
            ),
            worker_builder=lambda ctx, artifacts: __import__(
                "platforms.myplatform.protocol_mailbox",
                fromlist=["MyWorker"],
            ).MyWorker(proxy=ctx.proxy, log_fn=ctx.log),
            register_runner=lambda worker, ctx, artifacts: worker.run(
                email=ctx.identity.email,
                password=ctx.password,
                otp_callback=artifacts.otp_callback,
            ),
            otp_spec=OtpSpec(wait_message="等待验证码邮件..."),
        )

    def check_valid(self, account: Account) -> bool:
        """检测账号是否有效"""
        return bool(account.token)
```

### 3. 声明平台能力

在 `resources/platform_capabilities.json` 中添加：

```json
{
  "myplatform": {
    "supported_executors": ["protocol"],
    "supported_identity_modes": ["mailbox"],
    "supported_oauth_providers": []
  }
}
```

系统启动时会自动扫描 `platforms/` 目录加载所有带 `@register` 装饰器的插件。

## 常见问题

### 验证码失败怎么办？

1. 确认验证码 provider 已正确配置（YesCaptcha Client Key 或本地 Solver）
2. 协议模式下优先使用远程验证码服务（YesCaptcha / 2Captcha）
3. 浏览器模式下 Camoufox 会自动尝试点击 Turnstile checkbox，失败时回退到远程 Solver
4. 如果持续失败，检查代理 IP 质量——高风险 IP 会触发更严格的验证

### 代理被封 / 注册失败率高？

1. 在代理管理页查看各代理的成功率，禁用低成功率代理
2. 使用住宅代理而非数据中心代理，通过率显著更高
3. 降低并发数，避免同一 IP 短时间内大量请求
4. 不同平台对 IP 的敏感度不同，可按平台分配代理池

### 浏览器模式需要什么额外配置？

```bash
# 安装 Playwright 浏览器
python3 -m playwright install chromium

# 安装 Camoufox（反指纹浏览器）
python3 -m camoufox fetch
```

浏览器模式支持 `headless`（无头）和 `headed`（有头）两种，在注册页的执行器选项中选择即可。

## 参与贡献

欢迎提交 Issue 和 Pull Request。

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/my-feature`
3. 提交更改：`git commit -m 'feat: add my feature'`
4. 推送分支：`git push origin feature/my-feature`
5. 提交 Pull Request

提交规范建议使用 [Conventional Commits](https://www.conventionalcommits.org/)：
- `feat:` 新功能
- `fix:` 修复
- `docs:` 文档
- `refactor:` 重构
- `test:` 测试

## 更新日志

详见 [GitHub Releases](https://github.com/lxf746/any-auto-register/releases)。

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=lxf746/any-auto-register&type=Date)](https://star-history.com/#lxf746/any-auto-register&Date)

## License

本项目采用 [AGPL-3.0](LICENSE) 许可证。个人学习和研究可自由使用；商业使用需遵守 AGPL-3.0 条款（衍生作品须开源）。
