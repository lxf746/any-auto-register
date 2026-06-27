# Phase 2: Connection Pooling - Context

**Gathered:** 2026-06-27
**Status:** Ready for planning
**Mode:** Codebase analysis + requirements

<domain>
## Phase Boundary

Оптимизировать использование соединений — database pooling, HTTP session pooling, browser instance pooling, pool monitoring.

</domain>

<decisions>
## Implementation Decisions

### 1. Database Connection Pooling
| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| SQLAlchemy QueuePool (default) | Built-in, works out of box | Defaults may be too small | ✅ Configure defaults |
| SQLAlchemy NullPool | No pooling, fresh connections | Performance hit | ❌ Not for production |
| AsyncPG pool | Native async, fast | Requires async engine | ⏳ Phase 2 async |

**Decision:** Configure QueuePool with production-ready defaults (pool_size=20, max_overflow=10, pool_recycle=3600).

### 2. HTTP Session Pooling
| Approach | Pros | Cons | Recommendation |
|----------|------|------|----------------|
| aiohttp.TCPConnector | Async, connection pooling | Requires async | ✅ For async paths |
| requests.Session reuse | Simple, sync works | No pooling across threads | ✅ For sync paths |
| httpx.AsyncClient | Modern, async | New dependency | ❌ Not needed |

**Decision:** Reuse existing sessions via ManagedSession mixin. Add pool monitoring.

### 3. Browser Instance Pooling
| Approach | Pros | Cons | Recommendation |
|----------|------|------|----------------|
| Turnstile solver pattern | Already works | asyncio.Queue only | ✅ Extend to other platforms |
| Manual pool per platform | Simple | Duplication | ❌ Not scalable |
| Central browser pool | Single source of truth | Complex | ⏳ Future milestone |

**Decision:** Extend turnstile solver's asyncio.Queue pattern to other high-frequency platforms.

### 4. Pool Monitoring
| Metric | Source | Implementation |
|--------|--------|----------------|
| DB pool status | SQLAlchemy pool.status() | Add /health endpoint |
| HTTP session count | Track active sessions | Add metrics counter |
| Browser pool size | asyncio.Queue.qsize() | Log periodically |

**Decision:** Add lightweight monitoring via existing health endpoint.

</decisions>

<code_context>
## Existing Code Insights

### Current Database Connection Management
- **Engine:** `core/db/engine.py:53` — bare `create_engine(url)` with zero pooling config
- **Sessions:** 94 `with Session(engine) as session:` call sites across codebase
- **Portal:** `customer_portal_api/app/db.py:21` — separate engine, also zero pooling config
- **No pool_pre_ping:** Stale connections not detected

### Current HTTP Session Management
- **requests.Session:** 7 classes (SMS providers, mailbox drivers, Any2API)
- **curl_cffi.Session:** 10 classes (platform clients) — most lack `close()` method
- **ManagedSession mixin:** `core/mixins/managed_session.py` — defined but NEVER USED
- **Local sessions:** Several functions create sessions and never close them

### Current Browser Instance Management
- **Turnstile solver:** `services/turnstile_solver/api_solver.py:71` — asyncio.Queue pool (only pooling in project)
- **Platform browsers:** ~15 call sites, all create browsers on-demand (no pooling)
- **PlaywrightExecutor:** `core/executors/playwright.py` — proper context manager
- **OAuthBrowser:** `core/oauth_browser.py` — proper cleanup in __exit__

### Key Files to Modify
1. `core/db/engine.py` — Add pool configuration
2. `core/mixins/managed_session.py` — Already exists, needs adoption
3. `infrastructure/health_runtime.py` — Add pool metrics
4. Platform clients — Add close() methods where missing

</code_context>

<specifics>
## Specific Ideas

### Phase 2 Deliverables
1. **POOL-01:** Configure database connection pooling (pool_size, max_overflow, pool_recycle, pool_pre_ping)
2. **POOL-02:** HTTP session pooling via ManagedSession mixin adoption
3. **POOL-03:** Browser instance pooling for high-frequency platforms
4. **POOL-04:** Pool monitoring and metrics in health endpoint

### Key Changes
- `core/db/engine.py` — Add pool configuration to create_engine()
- `core/mixins/managed_session.py` — Verify and document usage pattern
- Platform clients — Add close() methods where missing
- `infrastructure/health_runtime.py` — Add pool status metrics
- `core/lifecycle.py` — Add engine.dispose() on shutdown

### Success Criteria
1. Database pool configured with production defaults
2. HTTP sessions reused via ManagedSession mixin
3. Browser contexts pooled for high-frequency platforms
4. Pool metrics available via health endpoint

</specifics>

<deferred>
## Deferred Ideas

- **Async session management** — Phase 2 async engine (future)
- **Central browser pool** — Complex, future milestone
- **Distributed connection pooling** — Requires Redis (v2)

</deferred>
