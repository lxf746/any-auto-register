# LuckMail Python SDK

LuckMail 邮件系统官方 Python SDK，支持**同步/异步双模式**，智能识别调用上下文自动切换，一套代码同时适配同步和异步场景。

## ✨ 特性

- 🔄 **智能同步/异步识别** — 同一方法，在普通函数中直接调用，在 async 函数中加 `await`，SDK 自动适配
- ⚡ **并发支持** — 异步模式下支持 `asyncio.gather` 并发接码
- 🔐 **双重鉴权** — 支持 API Key 普通模式和 HMAC 签名高安全模式
- 🎯 **一键接码** — `client.create_and_wait()` 一行代码完成创单+轮询全流程
- 📦 **完整覆盖** — 覆盖用户端和供应商端全部 API 接口
- 🛡️ **类型安全** — 所有响应均有对应数据模型（dataclass），告别 dict 地狱

## 📦 安装

```bash
# 推荐（支持异步）
pip install httpx

# 或仅需同步
pip install requests

# 安装 SDK（从源码）
cd sdk/python
pip install -e .
```

## 🚀 快速开始

### 初始化客户端

```python
from luckmail import LuckMailClient

client = LuckMailClient(
    base_url="https://your-domain.com",   # 平台地址
    api_key="your_api_key_here",           # 在「个人设置」页面生成
)
```

> 仅调用 `get_token_code`、`check_token_alive`、`get_token_mails`、`get_token_mail_detail` 这类 token-only 接口时，可传空 `api_key=""`。

### 同步调用（直接调用，无需 await）

```python
# 查询余额
balance = client.user.get_balance()
print(f"余额: {balance}")

# 一键接码
result = client.create_and_wait("twitter")
if result.status == "success":
    print(f"✅ 验证码: {result.verification_code}")
```

### 异步调用（加 await，代码几乎相同）

```python
import asyncio

async def main():
    # 查询余额
    balance = await client.user.get_balance()
    print(f"余额: {balance}")

    # 一键接码
    result = await client.create_and_wait("twitter")
    if result.status == "success":
        print(f"✅ 验证码: {result.verification_code}")

asyncio.run(main())
```

> **核心设计**：同一个 `client` 对象、同一套方法，在 `async` 函数中调用自动走异步通道，在普通函数中调用自动走同步通道，零配置切换。

---

## 📖 用户端 API

### 用户信息

```python
# 获取用户信息
info = client.user.get_user_info()
print(info.username, info.email, info.balance)

# 仅查询余额
balance = client.user.get_balance()
```

### 项目列表

```python
result = client.user.get_projects(page=1, page_size=50)
for project in result.list:
    print(f"[{project.code}] {project.name} - 超时: {project.timeout_seconds}s")
    for price in project.prices:
        print(f"  {price.email_type}: 接码 {price.code_price} / 购买 {price.buy_price}")
```

### 接码订单

#### 方式一：一键接码（推荐）

```python
# 创建订单 + 自动轮询，一行搞定
result = client.create_and_wait(
    project_code="twitter",
    email_type="ms_graph",      # 可选，指定邮箱类型
    domain="outlook.com",       # 可选，指定域名
    timeout=300,                # 最大等待 300 秒
    interval=3.0,               # 每 3 秒查询一次
)

if result.status == "success":
    print(f"验证码: {result.verification_code}")
    print(f"来自: {result.mail_from}")
    print(f"标题: {result.mail_subject}")
    print(f"HTML: {result.mail_body_html}")
else:
    print(f"接码失败: {result.status}")  # timeout / cancelled
```

#### 方式二：手动控制

```python
# 创建订单
order = client.user.create_order(
    project_code="twitter",
    email_type="ms_graph",
    domain="outlook.com",
)
print(f"订单号: {order.order_no}")
print(f"分配邮箱: {order.email_address}")

# 单次查询
code = client.user.get_order_code(order.order_no)
print(f"当前状态: {code.status}")

# 等待验证码（自动轮询）
result = client.user.wait_for_code(
    order.order_no,
    timeout=300,
    interval=3.0,
    on_poll=lambda r: print(f"轮询: {r.status}"),
)

# 取消订单
client.user.cancel_order(order.order_no)

# 查看历史订单
orders = client.user.get_orders(status=2)  # status=2 已完成
```

**订单状态说明：**
| status | 含义 |
|--------|------|
| `pending` | 待接码 |
| `success` | 接码成功 |
| `timeout` | 超时未收到 |
| `cancelled` | 已取消 |

### 购买邮箱

```python
# 购买邮箱
result = client.user.purchase_emails(
    project_code="twitter",
    quantity=5,
    email_type="ms_graph",
)
print(f"消费: {result['total_cost']}, 剩余: {result['balance_after']}")
for item in result["purchases"]:
    print(f"邮箱: {item['email_address']}, Token: {item['token']}")

# 查看已购列表
purchases = client.user.get_purchases(page=1, page_size=20)

# 通过 Token 获取验证码（一次性查询）
code = client.user.get_token_code("tok_abc123def456")
if code.has_new_mail:
    print(f"验证码: {code.verification_code}")

# 通过 Token 测活（可免 API Key，只传 token）
alive = client.user.check_token_alive("tok_abc123def456")
print(alive.alive, alive.message, alive.mail_count)

# 通过 Token 等待验证码（自动轮询）
result = client.user.wait_for_token_code("tok_abc123def456", timeout=120)
if result.has_new_mail:
    print(f"验证码: {result.verification_code}")
```

### 邮箱管理

```python
# 获取支持的邮箱类型
types = client.user.get_email_types()

# 我的邮箱列表
emails = client.user.get_emails(page=1, keyword="outlook", status=1)

# 导入邮箱
result = client.user.import_emails(
    email_type="ms_graph",
    emails=[
        {
            "address": "user@outlook.com",
            "password": "password123",
            "client_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            "refresh_token": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        }
    ]
)
print(f"成功: {result.success}, 重复: {result.duplicate}, 失败: {result.failed}")

# 导出邮箱（返回 bytes）
content = client.user.export_emails(keyword="outlook", status=1)
with open("my_emails.txt", "wb") as f:
    f.write(content)
```

### 申述

```python
result = client.user.create_appeal(
    appeal_type=1,           # 1=接码订单 2=购买邮箱
    order_id=123,            # 接码订单 ID
    reason="no_code",
    description="等待 5 分钟未收到验证码",
    evidence_urls=["https://example.com/screenshot.png"]
)
print(f"申述单号: {result['appeal_no']}")
```

---

## 📖 供应商端 API

```python
# 个人信息
profile = client.supplier.get_profile()
print(f"余额: {profile.balance}, 佣金率: {profile.code_commission_rate}")

# 数据看板
summary = client.supplier.get_dashboard()
print(f"总邮箱: {summary.total_emails}")
print(f"今日接码: {summary.today_assigned}, 成功: {summary.today_success}")
print(f"成功率: {summary.success_rate:.1f}%")
print(f"今日佣金: {summary.today_commission}")

# 邮箱列表
emails = client.supplier.get_emails(
    email_type="ms_graph",
    is_short_term=0,   # 0=长效 1=短效
    status=1
)

# 导入邮箱
result = client.supplier.import_emails(
    email_type="ms_graph",
    is_short_term=0,
    emails=[
        {
            "address": "user1@outlook.com",
            "client_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            "refresh_token": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        }
    ]
)

# 导出邮箱
content = client.supplier.export_emails(email_type="ms_graph", is_short_term=0)

# 申述管理
appeals = client.supplier.get_appeals(status=1)  # 待处理
detail = client.supplier.get_appeal("APL20240310001")

# 处理申述
client.supplier.reply_appeal(
    "APL20240310001",
    result=1,   # 1=同意退款 2=拒绝 3=申请仲裁
    reply="核查后确认邮箱有问题，同意退款"
)

# 批量处理
client.supplier.batch_reply_appeals(
    appeal_nos=["APL001", "APL002"],
    result=2,
    reply="邮箱状态正常，拒绝申述"
)
```

---

## 🔐 鉴权模式

### 普通 API Key 模式（默认）

```python
client = LuckMailClient(
    base_url="https://your-domain.com",
    api_key="your_api_key_here",
)
```

请求头：`X-API-Key: your_api_key_here`

### HMAC 签名模式（高安全性）

```python
client = LuckMailClient(
    base_url="https://your-domain.com",
    api_key="your_api_key_here",
    api_secret="your_api_secret_here",
    use_hmac=True,
)
```

自动生成并附加以下请求头：
```
X-API-Key: <api_key>
X-Timestamp: <unix_timestamp>
X-Nonce: <random_string>
X-Signature: <hmac_sha256_signature>
```

---

## ⚡ 异步并发示例

```python
import asyncio
from luckmail import LuckMailClient

client = LuckMailClient(base_url="https://...", api_key="...")

async def main():
    # 并发创建 3 个订单
    orders = await asyncio.gather(
        client.user.create_order("twitter"),
        client.user.create_order("facebook"),
        client.user.create_order("google"),
    )

    # 并发等待验证码
    results = await asyncio.gather(*[
        client.user.wait_for_code(o.order_no, timeout=300)
        for o in orders
    ])

    for i, r in enumerate(results):
        status = "✅" if r.status == "success" else "❌"
        print(f"订单 {i+1}: {status} {r.verification_code}")

asyncio.run(main())
```

---

## 🔧 异常处理

```python
from luckmail import LuckMailClient, APIError, AuthError, NetworkError, TimeoutError

client = LuckMailClient(...)

try:
    result = client.user.get_balance()
except AuthError as e:
    print(f"鉴权失败: {e}")           # API Key 无效或已过期
except APIError as e:
    print(f"API 错误 [{e.code}]: {e.message}")   # 业务逻辑错误
except TimeoutError as e:
    print(f"请求超时: {e}")
except NetworkError as e:
    print(f"网络错误: {e}")
```

---

## 📁 项目结构

```
sdk/python/
├── luckmail/
│   ├── __init__.py      # 包入口，导出所有公共符号
│   ├── client.py        # 主客户端 LuckMailClient
│   ├── http_client.py   # HTTP 客户端（同步/异步核心）
│   ├── user.py          # 用户端 API
│   ├── supplier.py      # 供应商端 API
│   ├── models.py        # 数据模型（dataclass）
│   └── exceptions.py    # 异常类
├── examples/
│   ├── user_sync.py     # 同步调用示例
│   └── user_async.py    # 异步调用示例
├── setup.py
└── README.md
```

---

## 📋 完整 API 速查表

### 用户端 (`client.user`)

| 方法 | 描述 |
|------|------|
| `get_user_info()` | 获取用户信息 |
| `get_balance()` | 查询余额 |
| `get_email_types()` | 获取支持的邮箱类型 |
| `get_emails(page, keyword, status)` | 我的邮箱列表 |
| `import_emails(type, emails)` | 导入邮箱 |
| `export_emails(keyword, status)` | 导出邮箱（bytes） |
| `get_projects(page, page_size)` | 获取项目列表 |
| `create_order(project_code, ...)` | 创建接码订单 |
| `get_order_code(order_no)` | 查询验证码（单次） |
| `wait_for_code(order_no, timeout)` | 等待验证码（自动轮询） |
| `cancel_order(order_no)` | 取消订单 |
| `get_orders(status, project_id)` | 查看订单列表 |
| `purchase_emails(project_code, qty)` | 购买邮箱 |
| `get_purchases(project_id)` | 已购邮箱列表 |
| `get_token_code(token)` | Token 查询验证码 |
| `wait_for_token_code(token, timeout)` | Token 等待验证码 |
| `create_appeal(...)` | 提交申述 |

### 供应商端 (`client.supplier`)

| 方法 | 描述 |
|------|------|
| `get_profile()` | 供应商个人信息 |
| `get_emails(type, is_short_term)` | 邮箱列表 |
| `import_emails(type, emails, ...)` | 导入邮箱 |
| `export_emails(...)` | 导出邮箱（bytes） |
| `get_appeals(status)` | 申述列表 |
| `get_appeal(appeal_no)` | 申述详情 |
| `reply_appeal(appeal_no, result, reply)` | 处理申述 |
| `batch_reply_appeals(appeal_nos, ...)` | 批量处理申述 |
| `get_dashboard()` | 数据看板总览 |

### 主客户端 (`client`)

| 方法 | 描述 |
|------|------|
| `create_and_wait(project_code, ...)` | 一键接码（创单+轮询） |

---

## 🛠️ 依赖

| 库 | 版本 | 用途 |
|----|------|------|
| `httpx` | ≥0.24 | 推荐，支持同步+异步 |
| `requests` | ≥2.28 | 可选，仅同步场景 |

Python 版本要求：≥3.8
