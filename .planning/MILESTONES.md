# Milestones

## v1.6 — Scaling & Performance

**Shipped:** 2026-06-27
**Phases:** 5 | **Plans:** 10 | **Tasks:** 23

### Key Accomplishments
- PostgreSQL migration with asyncpg, Alembic, engine auto-detection, SQLite fallback
- Connection pooling: QueuePool, ManagedSession mixin, BrowserPool, pool metrics
- Concurrent registration: priority queue dispatch, ResourceMonitor, priority-based claiming
- Rate limiting: PlatformRateLimiter, ProviderRateLimiter, exponential backoff, /api/rate-limits
- Gap closure: BrowserPool integrated into 3 platforms, rate limits enforced, retry utility integrated

### Requirements
- 17/17 satisfied (PG-01–05, POOL-01–04, CONC-01–04, RATE-01–04)

---

## v1.5 — Enterprise Cleanup

**Shipped:** 2026-06-27

### Key Accomplishments
- Split monoliths: base_sms→7, db→4, tasks→3, browser_register→12, account_graph→5 modules
- Extracted patterns: ManagedSession, BasePollingMailbox, retry utility, make_provider_resource
- Merged duplicates: consolidated core/mailbox/ vs providers/mailbox/
- Type safety: BasePlatform hints, RegistrationContext/IdentityMaterial Any replaced

---

## v1.4 — Memory Leaks & Thread Safety

**Shipped:** 2026-06-27

### Key Accomplishments
- HTTP session lifecycle management with proper cleanup
- Browser resources: TempWeb context manager, turnstile_solver guard
- Thread safety: _task_locks cleanup, _FERNET lock, registry locks, solver_manager lock
- Shutdown: Scheduler/LifecycleManager/TaskRuntime join threads, pipe cleanup

---

## v1.3 — Enterprise Email Provider Abstractions

**Shipped:** 2026-06-27

### Key Accomplishments
- Split core/base_mailbox.py into core/mailbox/ package
- Unified registry, typed config, resilience layer
- 17 requirements complete

---

## v1.2 — Remove Electron

**Shipped:** 2026-06-27

### Key Accomplishments
- Electron removed, React frontend kept
- desktop_apps.py (IDE detection) preserved as core feature

---

## v1.1 — Tech Debt & Code Quality

**Shipped:** 2026-06-27

### Key Accomplishments
- DEPR, DRY, MIGR, LOG, ERR, CONST — all complete

---

## v1.0 — Security Hardening

**Shipped:** 2026-06-27

### Key Accomplishments
- AUTH-01–05, DATA-01–03, VALD-01 — all complete
