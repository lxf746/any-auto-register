# Phase 5: Gap Closure - Context

**Gathered:** 2026-06-27
**Status:** Ready for planning
**Mode:** Audit gap closure

<domain>
## Phase Boundary

Закрытие гэпов из milestone audit — интеграция BrowserPool, подключение rate limiting, удаление мёртвого кода, интеграция retry utility.

</domain>

<decisions>
## Implementation Decisions

### 1. BrowserPool Integration
| Approach | Pros | Cons | Recommendation |
|----------|------|------|----------------|
| Integrate into turnstile solver | Direct use case | Solver is separate subprocess | ❌ Too complex |
| Integrate into platform browser code | Multiple use cases | Requires platform changes | ✅ Recommended |
| Keep as utility, add example | Minimal change | Still orphaned | ❌ Not fixing gap |

**Decision:** Integrate BrowserPool into platform browser registration flows (Windsurf, Blink, OpenBlockLabs).

### 2. Rate Limiting Integration
| Approach | Pros | Cons | Recommendation |
|----------|------|------|----------------|
| Add to platform registration | Direct enforcement | Multiple touch points | ✅ Recommended |
| Add to task runner | Centralized | Less granular | ⏳ Alternative |
| Add to HTTP client | Global enforcement | Too broad | ❌ Not targeted |

**Decision:** Add rate limit checks to platform registration code and task runner.

### 3. Dead Code Removal
| Code | Location | Action |
|------|----------|--------|
| claim_next_runnable_task | task_scheduler.py | Remove (duplicate) |
| mark_incomplete_tasks_interrupted | task_scheduler.py | Remove (duplicate) |
| request_cancel | task_scheduler.py | Remove (duplicate) |

**Decision:** Remove duplicate functions from task_scheduler.py.

### 4. Retry Utility Integration
| Approach | Pros | Cons | Recommendation |
|----------|------|------|----------------|
| Integrate into HTTPClient | Direct use case | Already has retry logic | ✅ Recommended |
| Integrate into task runner | Centralized | Less targeted | ⏳ Alternative |
| Keep as utility, add example | Minimal change | Still orphaned | ❌ Not fixing gap |

**Decision:** Integrate retry_with_backoff into HTTPClient request method.

</decisions>

<code_context>
## Existing Code Insights

### BrowserPool (core/turnstile_pool.py)
- Full asyncio.Queue-based pool with acquire/release/close
- Only imported in tests/test_browser_pool.py
- Needs integration into platform browser code

### Rate Limiters (core/rate_limiter.py)
- PlatformRateLimiter with check_platform_limit() method
- ProviderRateLimiter with check_provider_limit() method
- RateLimitMetrics with record_usage/hit/throttle methods
- Never called from production code

### Dead Code (application/tasks/task_scheduler.py)
- claim_next_runnable_task (line 95) — duplicate of task_repository.py
- mark_incomplete_tasks_interrupted (line 50) — duplicate
- request_cancel (line 73) — duplicate

### Retry Utility (core/utils/retry.py)
- retry decorator and retry_with_backoff function
- Exponential backoff with jitter support
- Never used by production code

</code_context>

<specifics>
## Specific Ideas

### Gap Closure Deliverables
1. **POOL-03:** Integrate BrowserPool into platform browser registration
2. **RATE-01:** Add check_platform_limit() to platform registration flows
3. **RATE-02:** Add check_provider_limit() to SMS/captcha provider flows
4. **RATE-03:** Add record_usage/throttle calls to rate limiting integration
5. **Dead Code:** Remove duplicate functions from task_scheduler.py
6. **Retry:** Integrate retry_with_backoff into HTTPClient

### Key Changes
- `platforms/windsurf/browser_register.py` — Use BrowserPool
- `platforms/blink/browser_register.py` — Use BrowserPool
- `platforms/openblocklabs/browser_register.py` — Use BrowserPool
- Platform registration files — Add rate limit checks
- `application/tasks/task_scheduler.py` — Remove dead code
- `core/http_client.py` — Integrate retry_with_backoff

### Success Criteria
1. BrowserPool used in at least 3 platform browser registrations
2. Rate limiting enforced in platform registration flows
3. Dead code removed from task_scheduler.py
4. Retry utility integrated into HTTPClient
5. All tests pass

</specifics>

<deferred>
## Deferred Ideas

None — this phase addresses all audit gaps.

</deferred>
