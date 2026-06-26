# Architecture

**Analysis Date:** 2026-06-26

## System Overview

```text
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Application                          │
│                     main.py (entry point)                        │
├─────────────────────────────────────────────────────────────────┤
│  api/            │  application/      │  core/                   │
│  (HTTP layer)    │  (service logic)   │  (domain + infra)        │
│  17 routers      │  ~15 services      │  base classes, registry  │
├──────────────────┴───────────────────┴──────────────────────────┤
│  domain/          │  infrastructure/   │  services/              │
│  (dataclasses)    │  (repositories)    │  (runtime workers)      │
├───────────────────┴────────────────────┴────────────────────────┤
│  platforms/        │  providers/        │  core/registration/     │
│  (plugin system)   │  (captcha/sms/etc) │  (flow orchestration)   │
│  14 platform mods  │  4 provider types  │  adapter pattern        │
├───────────────────┴────────────────────┴────────────────────────┤
│  core/db.py  (SQLite + SQLModel ORM)                            │
│  core/executors/  (protocol / headless / headed HTTP clients)    │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  frontend/  (Vite + TypeScript SPA, served as static files)     │
│  electron/  (Electron wrapper, optional desktop app)            │
└─────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| FastAPI app | HTTP entry, middleware, router registration | `main.py` |
| Auth middleware | Bearer-token / cookie auth | `core/auth.py` |
| API routers | HTTP request/response handling, Pydantic models | `api/*.py` |
| Application services | Business logic, orchestration, serialization | `application/*.py` |
| Domain layer | Dataclasses, command/query objects, no logic | `domain/*.py` |
| Repositories | DB access, SQL queries, data mapping | `infrastructure/*.py` |
| SQLModel tables | ORM models, schema, migrations | `core/db.py` |
| Platform registry | Auto-discovery + registration of platform plugins | `core/registry.py` |
| Base platform | ABC for platform plugins, registration flow dispatch | `core/base_platform.py` |
| Platform plugins | Concrete registration logic per platform | `platforms/*/plugin.py` |
| Registration flows | Orchestrate mailbox/browser/OAuth registration | `core/registration/flows.py` |
| Registration adapters | Platform-specific adapters for each flow type | `core/registration/adapters.py` |
| Executor abstraction | HTTP client layer (protocol/headless/headed) | `core/base_executor.py`, `core/executors/*.py` |
| Captcha abstraction | ABC + factory for captcha solvers | `core/base_captcha.py` |
| Identity abstraction | Mailbox/OAuth identity resolution | `core/base_identity.py` |
| Mailbox abstraction | ABC for temporary email services | `core/base_mailbox.py` |
| SMS abstraction | ABC for SMS verification providers | `core/base_sms.py` |
| Provider registry | Auto-discovery of captcha/sms/mailbox/proxy providers | `providers/registry.py` |
| Provider implementations | Concrete captcha/sms/mailbox/proxy providers | `providers/*/` |
| Task runtime | Background task dispatcher (threading) | `services/task_runtime.py` |
| Task orchestration | Task lifecycle, execution, logging | `application/tasks.py` |
| Lifecycle manager | Periodic account checks, token refresh, CPA sync | `core/lifecycle.py` |
| Scheduler | Trial expiry checks (hourly) | `core/scheduler.py` |
| Solver manager | Turnstile solver subprocess management | `services/solver_manager.py` |
| Proxy pool | Round-robin proxy rotation with health tracking | `core/proxy_pool.py` |
| Capability registry | Standard capability definitions for platform actions | `core/capability_registry.py` |
| Account graph | Multi-table account data assembly | `core/account_graph.py` |

## Pattern Overview

**Overall:** Layered Architecture with Plugin System + Adapter Pattern

**Key Characteristics:**
- **4-layer separation**: API → Application → Infrastructure → Core/Domain
- **Plugin-based platforms**: 14 platform plugins auto-discovered at startup via `core/registry.py`
- **Provider registry**: 4 provider types (captcha, sms, mailbox, proxy) auto-discovered via `providers/registry.py`
- **Adapter pattern** for registration flows: Browser, ProtocolMailbox, ProtocolOAuth adapters per platform
- **Strategy pattern** for executors: protocol (curl_cffi), headless (Playwright), headed (Playwright)
- **Background task system**: Thread-based task runtime with platform-aware concurrency limits

## Layers

**API Layer (`api/`):**
- Purpose: HTTP request handling, Pydantic request/response models, HTTP error mapping
- Location: `api/*.py` (17 routers)
- Contains: FastAPI routers with dependency injection of services
- Depends on: `application/`, `domain/`
- Used by: `main.py`

**Application Layer (`application/`):**
- Purpose: Business logic, orchestration, data transformation, serialization
- Location: `application/*.py` (~15 services)
- Contains: Service classes that coordinate domain objects and infrastructure
- Depends on: `domain/`, `infrastructure/`, `core/`
- Used by: `api/`

**Domain Layer (`domain/`):**
- Purpose: Pure data structures, command/query objects, no business logic
- Location: `domain/*.py`
- Contains: `@dataclass` definitions (AccountRecord, TaskSummary, etc.)
- Depends on: nothing (pure Python)
- Used by: `application/`, `infrastructure/`, `api/`

**Infrastructure Layer (`infrastructure/`):**
- Purpose: Database access, repository pattern, runtime services
- Location: `infrastructure/*.py` (10 repositories + runtime services)
- Contains: Repository classes wrapping SQLModel sessions
- Depends on: `core/db.py`, `domain/`
- Used by: `application/`

**Core Layer (`core/`):**
- Purpose: Domain abstractions, base classes, platform/executor/captcha/identity ABCs, registration orchestration
- Location: `core/*.py`, `core/registration/`, `core/executors/`
- Contains: ABCs, registries, flow orchestration, DB models, utilities
- Depends on: `providers/`, `infrastructure/` (selectively)
- Used by: `application/`, `platforms/`, `services/`

**Platform Plugins (`platforms/`):**
- Purpose: Concrete registration/check/action implementations per platform
- Location: `platforms/*/plugin.py` (14 platforms)
- Contains: `@register`-decorated classes extending `BasePlatform`
- Depends on: `core/registration/`, `core/base_platform.py`
- Used by: `core/registry.py` (auto-discovered)

**Provider Plugins (`providers/`):**
- Purpose: Concrete captcha/sms/mailbox/proxy provider implementations
- Location: `providers/{captcha,sms,mailbox,proxy}/*.py`
- Contains: `@register_provider`-decorated classes
- Depends on: `core/base_captcha.py`, `core/base_mailbox.py`, `core/base_sms.py`
- Used by: `providers/registry.py` (auto-discovered)

**Services (`services/`):**
- Purpose: Background runtime processes
- Location: `services/task_runtime.py`, `services/solver_manager.py`
- Contains: Thread-based task dispatcher, subprocess manager
- Depends on: `application/tasks.py`, `core/`
- Used by: `main.py` (lifespan)

## Data Flow

### Registration Task (Primary Flow)

1. **HTTP request** → `api/task_commands.py:create_task()` — receives registration parameters (platform, count, email, proxy, extra)
2. **Task creation** → `application/tasks.py:create_register_task()` — creates `TaskModel` in DB, status=`pending`
3. **TaskRuntime polls** → `services/task_runtime.py:_loop()` — claims pending tasks, spawns worker thread
4. **Task execution** → `application/tasks.py:_execute_register_task()` — orchestrates the registration loop
5. **Platform instantiation** → `core/registry.py:get(platform_name)` — looks up platform class, creates instance with `RegisterConfig`
6. **Identity resolution** → `core/base_platform.py:_resolve_identity()` — mailbox or OAuth identity provider
7. **Registration flow dispatch** → `core/base_platform.py:register()` — chooses BrowserRegistrationFlow / ProtocolMailboxFlow / ProtocolOAuthFlow
8. **Adapter execution** → `core/registration/flows.py` — runs platform-specific adapter (worker_builder → register_runner → result_mapper)
9. **Account persistence** → `core/db.py:save_account()` — upserts `AccountModel` + syncs `AccountOverviewModel`, `AccountCredentialModel`, etc.
10. **Result reporting** → `TaskLogger` updates task progress, events, and final status in DB

### Account Check Flow

1. **HTTP request** → `api/account_checks.py` — triggers check for single or all accounts
2. **Task creation** → `application/tasks.py:create_account_check_task()`
3. **Task execution** → `_run_single_account_check()` — loads account, instantiates platform plugin, calls `plugin.check_valid()`
4. **Status update** → `patch_account_graph()` — updates `AccountOverviewModel` with validity status

### Account List Query

1. **HTTP request** → `api/accounts.py:list_accounts()` — GET /api/accounts with filters
2. **Service call** → `application/accounts.py:AccountsService.list_accounts()`
3. **Repository query** → `infrastructure/accounts_repository.py:AccountsRepository.list()` — SQLModel query + account graph assembly
4. **Account graph loading** → `core/account_graph.py:load_account_graphs()` — joins AccountModel + AccountOverviewModel + credentials + provider data
5. **Serialization** → `_serialize()` returns dict with all account fields

**State Management:**
- SQLite database (file-based, single-process)
- Thread-safe via `threading.Lock` per task ID in `application/tasks.py`
- No external message queue — TaskRuntime polls DB every 0.5s
- Account state spread across multiple tables: `accounts`, `account_overviews`, `account_credentials`, `provider_accounts`, `provider_resources`

## Key Abstractions

**BasePlatform:**
- Purpose: ABC that every platform plugin extends. Defines registration, validation, action execution interfaces.
- Examples: `platforms/chatgpt/plugin.py`, `platforms/windsurf/plugin.py`, `platforms/kiro/plugin.py`
- Pattern: Template Method — `register()` calls abstract methods `build_browser_registration_adapter()`, `build_protocol_mailbox_adapter()`, etc.

**Registration Flow / Adapter:**
- Purpose: Decouple flow orchestration from platform-specific logic
- Examples: `core/registration/flows.py`, `core/registration/adapters.py`
- Pattern: Adapter + Strategy — each platform provides adapters with callbacks for worker_builder, register_runner, result_mapper

**BaseExecutor:**
- Purpose: Abstract HTTP client layer supporting protocol/headless/headed modes
- Examples: `core/executors/protocol.py` (curl_cffi), `core/executors/playwright.py` (Playwright)
- Pattern: Strategy — platform creates executor via `_make_executor()` based on `RegisterConfig.executor_type`

**BaseCaptcha / BaseMailbox / BaseSMS:**
- Purpose: Abstract external service integrations
- Examples: `core/base_captcha.py`, `core/base_mailbox.py`, `core/base_sms.py`
- Pattern: Abstract Factory + Registry — concrete implementations auto-discovered and instantiated from DB config

**TaskRuntime:**
- Purpose: Background task execution engine
- Examples: `services/task_runtime.py`
- Pattern: Worker pool with platform-aware concurrency limits (max 3 parallel, 1 per platform)

## Entry Points

**FastAPI main:**
- Location: `main.py`
- Triggers: `uvicorn.run()` or Docker entrypoint
- Responsibilities: App lifecycle (init_db, load_all, start services), router registration, SPA fallback

**Turnstile Solver subprocess:**
- Location: `services/turnstile_solver/start.py` (invoked via `--solver` flag)
- Triggers: `main.py --solver` or `solver_manager.py` spawns it
- Responsibilities: Standalone Quart server on port 8889 for Turnstile captcha solving

**Electron desktop app:**
- Location: `electron/main.js`
- Triggers: User launches desktop app
- Responsibilities: Wraps the web UI + backend in Electron

**Customer Portal API:**
- Location: `customer_portal_api/main.py`
- Triggers: Separate Docker service
- Responsibilities: Separate API for customer-facing portal

## Architectural Constraints

- **Threading:** Single-process, multi-threaded. TaskRuntime uses `ThreadPoolExecutor` (max 3 workers). SQLite is accessed via synchronous SQLModel sessions (thread-local). Platform plugins run in worker threads.
- **Global state:** `core/registry.py` has module-level `_registry` dict. `core/db.py` has module-level `engine`. `providers/registry.py` has module-level `_registry`. `services/task_runtime.py` has module-level `task_runtime` singleton. `core/lifecycle.py` has module-level `lifecycle_manager`.
- **No async in core:** Despite FastAPI being async, all platform/plugin code is synchronous. Task execution is fully synchronous in threads. Only the API layer uses `async` for request handling.
- **SQLite single-writer:** Database is SQLite (single-file). Concurrent writes are serialized by SQLite. Thread safety relies on SQLite's built-in locking + per-task locks in application/tasks.py.
- **Plugin auto-discovery:** Platform plugins are loaded via `pkgutil.iter_modules()` at startup. Provider plugins via same mechanism. Adding a new platform = adding `platforms/{name}/plugin.py` with `@register` decorator.

## Anti-Patterns

### Mixed domain and DB models

**What happens:** `core/db.py` contains SQLModel table definitions AND `save_account()` function with business logic (upsert logic, graph sync).
**Why it's wrong:** The domain layer (`domain/accounts.py`) is pure dataclasses, but the actual "save" logic lives in the DB module, blurring the line between persistence and domain.
**Do this instead:** Move `save_account()` and related functions to `infrastructure/accounts_repository.py`. Keep `core/db.py` focused on schema definitions and engine setup.

### Direct DB session access in application layer

**What happens:** `application/tasks.py` directly creates `Session(engine)` and runs queries (e.g., `create_register_task`, `_run_single_account_check`).
**Why it's wrong:** Bypasses the repository pattern established in `infrastructure/`. Makes testing harder.
**Do this instead:** Route all DB access through `infrastructure/` repositories. Application layer should only call repository methods.

### Synchronous platform code in async FastAPI

**What happens:** Platform registration (`platform.register()`) is synchronous and blocks the thread. FastAPI runs endpoints in a threadpool for sync handlers, but the task runtime is entirely synchronous.
**Why it's wrong:** Potential thread starvation if many tasks run simultaneously. Currently mitigated by `max_parallel_tasks=3`.
**Do this instead:** This is a known trade-off. For now the threading model works. If scaling is needed, consider async executors or process-based isolation.

### Large `application/tasks.py` (959 lines)

**What happens:** Single file contains task creation, serialization, execution orchestration, all task type handlers, and helper functions.
**Why it's wrong:** Hard to navigate, test, and modify. Each task type handler is independent but coupled in one file.
**Do this instead:** Split into `application/task_handlers/register.py`, `application/task_handlers/check.py`, etc. Keep `application/tasks.py` as the orchestration layer only.

## Error Handling

**Strategy:** Exception-based with try/except at task boundaries. Errors are recorded in task events and task result JSON.

**Patterns:**
- Platform registration catches exceptions per-account in the registration loop, records errors via `TaskLogger.record_error()`, continues with next account
- API layer uses `HTTPException` for 404/400 responses
- Task execution wraps handlers in try/except, finishes task with `TASK_STATUS_FAILED` on unhandled exceptions
- Solver manager tracks consecutive failures to prevent infinite retry loops

## Cross-Cutting Concerns

**Logging:** Mixed — `print()` statements throughout (e.g., `main.py`, `core/registry.py`), `logging.getLogger()` in `core/lifecycle.py`, `TaskLogger` for task-specific events. No unified logging framework.

**Validation:** Pydantic models in API layer for request validation. Domain dataclasses use `Optional` fields. No schema validation at the DB level beyond SQLModel field types.

**Authentication:** Simple bearer-token middleware (`core/auth.py`). Password set via `APP_PASSWORD` env var. Health endpoints are public. No RBAC, no user management.

**Configuration:** Environment variables for DB URL, app password. `core/config_store.py` for runtime config (stored in DB). Provider settings stored in `provider_settings` table.

---

*Architecture analysis: 2026-06-26*
