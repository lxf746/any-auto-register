<div align="center">

# Any Auto Register

11+ AI 平台账号自动化注册与管理 · 协议 / 浏览器双模式 · Mac / Windows 桌面版一键启动

<p>
  <a href="https://github.com/lxf746/any-auto-register/stargazers"><img src="https://img.shields.io/github/stars/lxf746/any-auto-register?style=flat-square&logo=github&color=FFB003" alt="Stars" /></a>
  <a href="https://github.com/lxf746/any-auto-register/releases/latest"><img src="https://img.shields.io/github/v/release/lxf746/any-auto-register?style=flat-square&logo=github&color=22c55e" alt="Release" /></a>
  <a href="https://github.com/lxf746/any-auto-register/releases"><img src="https://img.shields.io/github/downloads/lxf746/any-auto-register/total?style=flat-square&logo=github&color=8b5cf6" alt="Downloads" /></a>
  <a href="https://github.com/lxf746/any-auto-register/network/members"><img src="https://img.shields.io/github/forks/lxf746/any-auto-register?style=flat-square&logo=github&color=3b82f6" alt="Forks" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/lxf746/any-auto-register?style=flat-square&color=f97316" alt="License" /></a>
</p>

<p>
  <a href="https://github.com/lxf746/any-auto-register/releases/latest"><b>下载桌面版</b></a>
  &nbsp;·&nbsp;
  <a href="#它解决什么">它解决什么</a>
  &nbsp;·&nbsp;
  <a href="#一眼看完">界面预览</a>
  &nbsp;·&nbsp;
  <a href="#社群">加入社群</a>
  &nbsp;·&nbsp;
  <a href="README_en.md">English</a>
  &nbsp;·&nbsp;
  <a href="README_vi.md">Tiếng Việt</a>
</p>

<img src="assets/screenshots/概览.png" alt="Any Auto Register Dashboard" width="92%" />

</div>

---

> **本仓库是 [`lxf746/any-auto-register`](https://github.com/lxf746/any-auto-register) 官方上游**,最早的原作者仓库与最及时的更新都在此处。其他同名 fork 均为二次开发分支。

> 本项目仅供学习与研究,不得用于商业违规用途。使用者需自行评估并遵守目标平台的服务条款,所产生的一切后果由使用者自行承担。

## 它解决什么

多数同类项目只解决"怎么注册某一个平台",留下大量工程化空白:邮箱怎么管、验证码怎么过、代理怎么轮换、注册成功后怎么持续用、Token 过期了怎么办、出错了怎么定位。Any Auto Register 把这些都做了。

| | 同类工具 | Any Auto Register |
|---|---|---|
| 部署 | 命令行 / Docker / .py 脚本 | 桌面客户端(Mac / Win)双击即用,内嵌 React UI |
| 平台覆盖 | 1-3 个 | 11+ 平台 + Anything 通用适配器,新平台插件式接入 |
| 邮箱方案 | 多数靠 IMAP | 9 种通道:MoeMail / Cloudflare 自建 / TempMail / DDG Email 等 |
| 执行模式 | 仅浏览器 | 纯协议(最快)/ Headless / Headed 三种 |
| 全生命周期 | 注册完丢一边 | 定时检测 + Token 续期 + Trial 预警 + 风险中心告警 |
| 数据分析 | 无 | 注册成功率仪表盘,错误归因(代理被风控 / 邮箱异常 / 二次验证) |
| API 网关联动 | 无 | 注册即推送 [Any2API](https://github.com/lxf746/any2api),统一接入 OpenAI 兼容协议层 |
| 架构 | 通常硬编码 | 全插件化:平台 / 邮箱 / 验证码 / 接码 / 代理 都可热插拔 |

配合 [`Any2API`](https://github.com/lxf746/any2api) 网关可以一键打通:批量注册账号 → 自动推送 → 立即作为 OpenAI / Claude 兼容 API 使用。

## 一眼看完

> 截图来自最新桌面版 (`v1.0.29`),随版本迭代持续更新。顶部 Hero 图即为概览仪表盘——总账号 / 存活 / 失效 / 今日注册 / 后台队列 / 失败重试 6 项核心指标实时显示,叠加注册成功率与生命周期监控双视图,右侧汇总本机运行环境。下面是其他工作区视图:

### 账号池 — 多平台账号统一管理

按平台分 Tab 展示,密码 / 管家 / 状态 / 额度 / 支付链接 / 最近查询时间一览,支持搜索、批量导入导出、单条复制 / 打开支付。

![账号池](assets/screenshots/账号池.png)

### 任务队列 — 批量注册与历史

集中查看全部 / 运行中任务,卡片显示平台、成功数 / 总数、时间戳与状态,可单任务查看实时日志、暂停全部、清空队列。

![任务队列](assets/screenshots/任务队列.png)

### 注册日志 — 实时步骤追踪

每一步注册过程通过 SSE 推送到前端,从 OAuth code 交换、Token 获取到额度查询全程可见,出错立即定位到具体步骤。

![注册日志](assets/screenshots/注册.png)

### 全局设置 — 桌面端偏好

主题 / 语言 / 全局默认代理,以及桌面端专属的开机自启、最小化到托盘、关闭最小化、启动检查更新、自动备份等行为开关。

![全局设置](assets/screenshots/设置.png)

## 核心能力

按职责分组:

**注册流程**

- **平台**:ChatGPT / Cursor / Kiro / Trae.ai / Tavily / Grok / Blink / Cerebras / OpenBlockLabs / Windsurf,以及 Anything 通用适配器
- **邮箱**:MoeMail 自建 / Cloudflare Worker 自建 / Laoudo / DuckMail / Testmail / Freemail / TempMail.lol / Temp-Mail Web / DuckDuckGo Email
- **验证码**:YesCaptcha / 2Captcha / 本地 Solver (Camoufox)
- **接码**:SMS-Activate / HeroSMS
- **执行模式**:协议(无浏览器,最快)/ Headless / Headed,按平台支持情况切换
- **本地 2FA**:内置 TOTP 计算,无需第三方应用获取动态码

**运营管理**

- **生命周期**:定时有效性检测 + Token 自动续期 + Trial 过期预警,首页一键执行续期
- **风险中心**:Token 已过期 / Trial 即将耗尽 / 代理连通异常 集中告警
- **成功率统计**:全局成功率 + 错误归因(一次性成功 / 二次验证 / 代理被风控 / 邮箱域名异常),按平台 / 按天 / 按代理细分
- **任务队列**:批量注册任务历史 + 实时进度 + 单任务日志

**系统能力**

- **代理池**:静态轮询(成功率加权)+ 动态 API 提取 + 旋转网关,失效自动禁用
- **Any2API 联动**:注册成功后自动推送账号到网关,即注册即用
- **导出格式**:JSON / CSV / CPA / Sub2API / Kiro-Go / Any2API admin.json
- **并发与日志**:可配置并发数,SSE 实时日志,持久化任务执行器
- **插件化**:平台 / 邮箱 / 验证码 / 接码 / 代理驱动 全部支持热插拔扩展

## 快速开始

### 桌面版(推荐)

> 🚀 零配置,Electron 内置完整后端 + 前端,双击即用。

| 平台 | 下载 |
|------|------|
| 🍎 macOS (Intel / Apple Silicon) | [Releases 下载 `.dmg`](https://github.com/lxf746/any-auto-register/releases/latest) |
| 🪟 Windows | [Releases 下载 `.exe`](https://github.com/lxf746/any-auto-register/releases/latest) |

下载安装 → 启动 → 输入激活码([加群获取](#社群))→ 选择平台 → 配置邮箱 → 开始注册。

### Docker

```bash
mkdir -p any-auto-register && cd any-auto-register

cat > docker-compose.yml <<'EOF'
services:
  app:
    image: ghcr.io/lxf746/any-auto-register:latest
    ports:
      - "8000:8000"   # Web UI
      - "6080:6080"   # noVNC 可视化浏览器
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

| 服务 | 地址 | 说明 |
|------|------|------|
| Web UI | `http://localhost:8000` | 主界面 |
| noVNC | `http://localhost:6080/vnc.html` | 可视化浏览器(headed 模式) |
| Solver | `http://localhost:8889` | Turnstile 验证码求解器 |

云服务器部署时请放行 `8000` / `6080` / `8889` 端口。

### 源码运行

> 源码包含核心注册流程与完整 provider 体系,适合二次开发和自部署。任务队列高级控制、激活码管理、支付流增强、最新平台适配的增强实现随桌面版发布。

需要 Python 3.11+ / Node.js 18+:

```bash
git clone https://github.com/lxf746/any-auto-register.git
cd any-auto-register/account_manager

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cd frontend && npm install && npm run build && cd ..

# 可选:浏览器模式需要
python3 -m playwright install chromium
python3 -m camoufox fetch

python3 -m uvicorn main:app --port 8000
```

浏览器访问 `http://localhost:8000`。前端开发模式见 [开发文档](#开发文档)。

## 配置详解

### 邮箱服务

注册时需要选择一种邮箱服务用于接收验证码。当前版本邮箱、验证码、接码配置由后端 provider catalog 驱动,前端"全局配置"页是列表式 CRUD:左侧已添加配置,右侧统一编辑;后端新增 provider 后,前端无需写死选项,刷新即可出现。

| Provider | 说明 |
|----------|------|
| **MoeMail**(推荐) | 基于 [cloudflare_temp_email](https://github.com/dreamhunter2333/cloudflare_temp_email) 自建临时邮箱,无需配置,自动注册账号生成邮箱 |
| **Laoudo** | 固定自有域名邮箱,稳定性最高,适合长期使用 |
| **Cloudflare Worker 自建** | 基于 cloudflare_temp_email 自行部署,完全自主可控 |
| **Testmail** | `testmail.app` namespace 模式,适合并发任务,自动 tag + 时间过滤 |
| **DuckDuckGo Email** | `@duck.com` 私密别名 + IMAP 转发读取 |
| **Freemail** | Cloudflare Worker 自建,支持管理员令牌或用户名密码认证 |
| **DuckMail** | 公共临时邮箱,无需配置,部分地区需代理 |
| **TempMail.lol** | 公共临时邮箱,自动生成匿名地址 |
| **Temp-Mail Web** | 基于 `web2.temp-mail.org` 的临时邮箱 |

各 Provider 字段格式参考全局配置页内字段提示,后端会按 provider catalog 自动渲染表单。

### 验证码服务

| 服务 | 说明 |
|------|------|
| YesCaptcha | 填写 Client Key,在 [yescaptcha.com](https://yescaptcha.com) 注册获取 |
| 2Captcha | 填写 API Key,在 [2captcha.com](https://2captcha.com) 注册获取 |
| 本地 Solver | Camoufox 本地解码,需先执行 `python3 -m camoufox fetch` |

### 代理池

| 🌟 推荐代理服务 | 简介说明 |
| :--- | :--- |
| <a href="https://www.swiftproxy.net/?ref=lxf746"><img src="assets/swiftproxy.svg" width="130" alt="Swiftproxy"/></a> | **[Swiftproxy](https://www.swiftproxy.net/?ref=lxf746)** — 80M+ 高质量住宅 IP，连接稳定高匿名，动态流量不过期，支持免费测试，完美适配自动化轮询。 |
| <a href="https://colaproxy.com/?utm_source=lxf746&utm_medium=lxf746&ref=lxf746"><img src="assets/colaproxy.png" width="130" alt="ColaProxy"/></a> | **[ColaProxy](https://colaproxy.com/?utm_source=lxf746&utm_medium=lxf746&ref=lxf746)** — 免费测试 90M+ 海外纯净 IP，单价低至 $0.3/GB，支持住宅 / 移动 / 静态 / 不限量代理，高速轮换 + 多账号环境隔离，降低封禁率。 |

- **静态代理**:代理管理页手动添加,系统按成功率加权轮询,连续失败 5 次自动禁用
- **API 提取代理**:通过 HTTP API 动态提取代理 IP,适用于大多数代理商
- **旋转网关代理**:固定入口地址、每次请求自动分配出口 IP,适用于 BrightData / Oxylabs / IPRoyal 等

数据库中启用 `proxy` provider 时,注册会优先尝试动态代理,失败或未配置自动回退到静态池。

### 接码服务

部分平台(如 Cursor)注册需要手机号验证:

| 服务 | 说明 |
|------|------|
| SMS-Activate | 填写 API Key,可配置默认国家 |
| HeroSMS | 填写 API Key,可配置服务代码、国家 ID、最高单价、号码复用策略 |

注册任务参数里指定 `sms_provider` 优先,未指定时使用默认接码 Provider。

## 进阶

### 账号生命周期

系统内置后台生命周期管理器,自动执行:

- **有效性检测**:每 6 小时检测活跃账号,失效标记为 invalid
- **Token 自动续期**:每 12 小时刷新即将过期的 token(当前支持 ChatGPT)
- **Trial 过期预警**:扫描 trial 账号,即将过期标记预警,已过期自动更新状态

也可 API 手动触发:`POST /api/lifecycle/{check|refresh|warn}`,`GET /api/lifecycle/status` 查看状态。

### 注册成功率与错误归因

- `GET /api/stats/overview` — 全局概览(总注册数、成功率、状态分布)
- `GET /api/stats/by-platform` — 按平台统计
- `GET /api/stats/by-day?days=30` — 按天趋势
- `GET /api/stats/by-proxy` — 代理成功率排行
- `GET /api/stats/errors?days=7` — 失败错误聚合

### Any2API 联动

配合 [Any2API](https://github.com/lxf746/any2api) 网关,注册完成自动推送账号,注册即可用。

全局配置中设置:

| 参数 | 说明 |
|------|------|
| `any2api_url` | Any2API 实例地址,如 `http://localhost:8099` |
| `any2api_password` | Any2API 管理密码 |

注册成功后自动推送对应平台资源:

| 平台 | 推送目标 |
|------|----------|
| Kiro | `kiroAccounts` 账号池 |
| Grok | `grokTokens` token 池 |
| Cursor | `cursorConfig` cookie |
| ChatGPT | `chatgptConfig` token |
| Blink | `blinkConfig` 凭证 |
| Windsurf | `windsurfAccounts` 账号池 |

未配置 `any2api_url` 时此功能静默跳过,不影响正常注册。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI + SQLite (SQLModel) |
| 前端 | React + TypeScript + Vite + TailwindCSS |
| HTTP | curl_cffi(浏览器指纹伪装) |
| 浏览器自动化 | Playwright / Camoufox |
| 桌面端 | Electron + Nuitka 打包 |

## 开发文档

<details>
<summary><b>项目结构</b></summary>

```
account_manager/
├── main.py                 # FastAPI 入口
├── api/                    # HTTP 路由层
│   ├── accounts.py         # 账号 CRUD + 导出
│   ├── account_providers.py     # 邮箱 / 验证 / 接码 / 代理
│   ├── registration.py          # 注册任务 + SSE
│   ├── query.py                 # 账号状态查询
│   ├── payment.py               # 支付链接 / 支付动作
│   ├── transfer.py              # 导入导出
│   ├── platforms.py             # 平台列表
│   ├── provider_definitions.py  # Provider 定义管理
│   ├── proxies.py               # 代理管理
│   ├── health.py                # 健康检查
│   └── system.py                # 系统设置 / Solver 管理
├── application/            # 应用服务层
├── domain/                 # 领域模型
├── infrastructure/         # 仓储与运行时适配
├── core/                   # 基础能力(平台 / 邮箱 / 验证码 / 接码 基类)
├── platforms/              # 平台插件层
├── providers/              # Provider 插件层
│   ├── mailbox/
│   ├── captcha/
│   ├── sms/
│   └── proxy/
├── services/               # 后台服务(Solver 进程 / 任务执行器)
├── customer_portal_api/    # C 端 / 管理端独立 API
├── electron/               # Electron 桌面端打包
├── tests/                  # 测试
└── frontend/               # React 前端
```

</details>

<details>
<summary><b>开发模式(前端热更新)</b></summary>

```bash
cd frontend
npm run dev
# 访问 http://localhost:5173,API 由 Vite 代理转发到后端
```

启动入口统一 `main:app`,后端接口统一 `/api/*`,前后端接口契约见 [docs/frontend-api-contract.md](docs/frontend-api-contract.md)。

</details>

<details>
<summary><b>新增平台插件</b></summary>

平台插件目录结构:

```
platforms/myplatform/
├── plugin.py
├── registration/
│   ├── module.py       # 注册模块入口
│   ├── protocol.py     # 协议核心
│   ├── worker.py       # mailbox provider 到协议流程
│   ├── browser.py      # 浏览器注册(按需)
│   └── oauth.py        # 浏览器 OAuth(按需)
├── query.py            # 查询能力(按需)
├── payment.py          # 支付能力(按需)
└── transfer.py         # 导入导出(按需)
```

最小实现 `plugin.py`:

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

系统启动时扫描 `platforms/*/plugin.py` 自动加载 `@register` 注册的插件。完整的 `registration/module.py` 示例参考已有平台(`platforms/kiro/`、`platforms/chatgpt/`)。

</details>

<details>
<summary><b>参与贡献</b></summary>

1. Fork 本仓库
2. 创建特性分支:`git checkout -b feature/my-feature`
3. 提交:`git commit -m 'feat: add my feature'`(建议遵循 [Conventional Commits](https://www.conventionalcommits.org/))
4. 推送:`git push origin feature/my-feature`
5. 提交 Pull Request

</details>

## 常见问题

<details>
<summary><b>验证码失败怎么办?</b></summary>

1. 确认验证码 provider 已正确配置(YesCaptcha Client Key 或本地 Solver)
2. 协议模式下优先使用远程验证码服务(YesCaptcha / 2Captcha)
3. 浏览器模式下 Camoufox 会自动尝试点击 Turnstile checkbox,失败时回退到远程 Solver
4. 持续失败检查代理 IP 质量——高风险 IP 会触发更严格的验证

</details>

<details>
<summary><b>代理被封 / 注册失败率高?</b></summary>

1. 代理管理页查看各代理成功率,禁用低成功率代理
2. 使用住宅代理而非数据中心代理,通过率显著更高
3. 降低并发数,避免同一 IP 短时间内大量请求
4. 不同平台对 IP 敏感度不同,可按平台分配代理池

</details>

<details>
<summary><b>Solver 启动超时怎么办?</b></summary>

`[Solver] 启动超时` 表示本地 Turnstile Solver 在 30 秒内没有通过健康检查,主服务仍然会继续启动。常见原因是首次启动需要下载或初始化 Camoufox、当前环境缺少浏览器依赖,或 8889 端口被占用。

1. 本地执行 `python3 -m camoufox fetch`,然后在"全局配置"页点击"重启 Solver"
2. 如不依赖本地 Solver,配置 YesCaptcha 或 2Captcha,注册任务中选择远程验证码
3. Docker 环境建议使用预构建镜像;本地裸跑持续超时优先检查 8889 端口和 Camoufox 安装

</details>

<details>
<summary><b>ARM 镜像构建失败?</b></summary>

如果日志里出现 `src/pages/Accounts.tsx ... TS6133/TS7006`,实际失败点是前端 TypeScript 构建,不是 ARM 或 apt 安装问题。先本地执行:

```bash
cd frontend && npm run build
```

确认前端构建通过后再执行:

```bash
docker compose build --no-cache && docker compose up -d
```

</details>

## 社群

加入用户群获取最新动态、激活码、配置经验和注册技巧:

| QQ 群 | 群号 | 状态 |
|---|---|---|
| 一群 | `1081650009` | 已满 |
| 二群 | `1097916468` | 已满 |
| 三群 | `100799970` | 已满 |
| 四群 | `469274724` | 已满 |
| 五群 | `906077873` | 可加入 |

直接在 QQ 中搜索群号加入。提交 Bug 或新功能请求请前往 [Issues](https://github.com/lxf746/any-auto-register/issues)。

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=lxf746/any-auto-register&type=Date)](https://star-history.com/#lxf746/any-auto-register&Date)

> 如果这个项目帮你省下了重复劳动的时间,点个 ⭐ 让更多人看到。

## 赞助商

<table>
<tr>
<td width="220" align="center">
<a href="https://www.rapidproxy.io/?ref=lxf" target="_blank">
<img src="https://www.rapidproxy.io/static/rapidproxy/images/rapid_logo_700.png" alt="RapidProxy" width="180" />
</a>
</td>
<td>
<b><a href="https://www.rapidproxy.io/?ref=lxf">RapidProxy</a></b> — 高质量住宅代理,智能 IP 轮换,低封禁率,流量不过期,助力数据采集。<br/>
90M+ 真实住宅 IP · 200+ 国家 / 地区 · 99.9% 在线率 · &lt;0.5s 响应。<br/>
<a href="https://www.rapidproxy.io/?ref=lxf"><b>免费试用 →</b></a>
</td>
</tr>
</table>

## License

本项目采用 [AGPL-3.0](LICENSE) 许可证。个人学习和研究可自由使用;商业使用需遵守 AGPL-3.0 条款(衍生作品须开源)。
