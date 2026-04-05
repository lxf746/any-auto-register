# Any Auto Register

> ⚠️ **免责声明**：本项目仅供学习和研究使用，不得用于任何商业用途。使用本项目所产生的一切后果由使用者自行承担。

多平台账号自动注册与管理系统，支持插件化扩展，内置 Web UI。

## 功能特性

- **多平台支持**：Trae.ai、Tavily、Cursor、Kiro、ChatGPT、OpenBlockLabs，支持自定义插件扩展
- **多邮箱服务**：MoeMail（自建）、Laoudo、DuckMail、Cloudflare Worker 自建邮箱
- **多执行模式**：API 协议（无浏览器）、无头浏览器、可视浏览器（各平台按需支持，OAuth 能力受平台和浏览器复用配置限制）
- **验证码服务**：YesCaptcha、2Captcha、本地 Solver（Camoufox）
- **代理池管理**：自动轮询、成功率统计、自动禁用失效代理
- **并发注册**：可配置并发数
- **实时日志**：SSE 实时推送注册日志到前端
- **平台扩展操作**：各平台可自定义操作（如 Kiro 账号切换、Trae Pro 升级链接生成）

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

浏览器访问 `http://localhost:5173`

说明：

- 启动入口统一为 `main:app`
- 后端接口统一位于 `/api/*`
- 前端默认直接请求 `/api`

### 开发模式（前端热更新）

```bash
cd frontend
npm run dev
# 访问 http://localhost:5173
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

## 验证码服务配置

| 服务 | 说明 |
|------|------|
| YesCaptcha | 需填写 Client Key，在 [yescaptcha.com](https://yescaptcha.com) 注册获取 |
| 本地 Solver | 使用 Camoufox 本地解码，需先执行 `python3 -m camoufox fetch` |

## 项目结构

```
account_manager/
├── main.py                 # FastAPI 入口
├── api/                    # HTTP 路由层
│   ├── accounts.py         # 账号 CRUD + 导出
│   ├── account_checks.py   # 账号检测
│   ├── task_commands.py    # 注册任务创建 + SSE
│   ├── tasks.py            # 任务查询
│   ├── task_logs.py        # 历史任务日志
│   ├── actions.py          # 平台操作
│   ├── config.py           # 配置读写
│   ├── platforms.py        # 平台列表
│   ├── platform_capabilities.py
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
│   ├── db.py               # 数据模型
│   ├── proxy_pool.py       # 代理池
│   ├── registry.py         # 平台插件注册表
│   └── scheduler.py        # 定时任务
├── platforms/              # 平台插件层
│   └── {platform}/
│       ├── plugin.py       # 平台适配层
│       ├── core.py         # 注册协议核心逻辑
│       └── switch.py       # 账号切换逻辑
├── services/               # 后台服务
│   ├── solver_manager.py   # Turnstile Solver 进程管理
│   └── task_runtime.py     # 持久化任务执行器
├── scripts/
│   └── smoke.py            # API 冒烟检查
└── frontend/               # React 前端
```

## 插件开发

添加新平台只需在 `platforms/` 下新建目录，实现 `plugin.py`：

```python
from core.base_platform import BasePlatform, Account, AccountStatus, RegisterConfig
from core.registry import register

@register
class MyPlatform(BasePlatform):
    name = "myplatform"
    display_name = "My Platform"
    version = "1.0.0"
    supported_executors = ["protocol"]

    def register(self, email: str, password: str = None) -> Account:
        # 用 self.mailbox.get_email() 获取邮箱
        # 用 self.mailbox.wait_for_code() 收验证码
        ...

    def check_valid(self, account: Account) -> bool:
        ...
```

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=lxf746/any-auto-register&type=Date)](https://star-history.com/#lxf746/any-auto-register&Date)

## License

MIT License — 仅供学习研究，禁止商业使用。
