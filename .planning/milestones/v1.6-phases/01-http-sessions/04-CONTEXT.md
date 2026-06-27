# Phase 4: Rate Limiting - Context

**Gathered:** 2026-06-27
**Status:** Ready for planning
**Mode:** Codebase analysis + requirements

<domain>
## Phase Boundary

Контроль скорости запросов к провайдерам — per-platform limits, per-provider limits, adaptive rate limiting, rate limit metrics.

</domain>

<decisions>
## Implementation Decisions

### 1. Per-Platform Rate Limits
| Platform | Current | Proposed | Implementation |
|----------|---------|----------|----------------|
| ChatGPT | None | 10 req/min | PlatformRateLimiter |
| Windsurf | None | 5 req/min | PlatformRateLimiter |
| Kimchi | Proxy rotation | 3 req/min | PlatformRateLimiter |
| Other platforms | None | 5 req/min | PlatformRateLimiter |

**Decision:** Create PlatformRateLimiter class with configurable per-platform limits.

### 2. Per-Provider Rate Limits
| Provider | Current | Proposed | Implementation |
|----------|---------|----------|----------------|
| Mailbox providers | 30 req/min (sliding window) | Keep existing | ResilientMailbox |
| SMS providers | None | 10 req/min | ProviderRateLimiter |
| Captcha solvers | None | 5 req/min | ProviderRateLimiter |

**Decision:** Extend existing RateLimiter pattern to SMS and captcha providers.

### 3. Adaptive Rate Limiting
| Strategy | Current | Proposed | Implementation |
|----------|---------|----------|----------------|
| Linear backoff | Yes (HTTPClient, tempmail) | Keep for simple cases | Existing code |
| Exponential backoff | No | Add for critical paths | core/utils/retry.py |
| Circuit breaker | Yes (mailbox) | Extend to platforms | PlatformRateLimiter |

**Decision:** Add exponential backoff option to retry utility, extend circuit breaker pattern.

### 4. Rate Limit Metrics
| Metric | Current | Proposed | Implementation |
|--------|---------|----------|----------------|
| Rate limit hits | No | Add counter | RateLimitMetrics |
| Current usage | No | Add gauge | RateLimitMetrics |
| Throttle events | No | Add counter | RateLimitMetrics |

**Decision:** Create RateLimitMetrics class, expose via /api/rate-limits endpoint.

</decisions>

<code_context>
## Existing Code Insights

### Current Rate Limiting Mechanisms
- **Mailbox resilience:** `core/mailbox/resilience.py` — RateLimiter (sliding window), CircuitBreaker
- **API auth:** `api/auth.py` — IP-based sliding window (5 req/5min)
- **HTTPClient:** `core/http_client.py` — Linear backoff retry on 5xx
- **TempMail Web:** `core/mailbox/tempmail_web.py` — 429 retry with linear+jitter
- **ResourceMonitor:** `core/db/engine.py` — CPU/memory throttle

### Current Patterns to Extend
1. **RateLimiter:** Already works for mailbox, extend to platforms
2. **CircuitBreaker:** Already works for mailbox, extend to platforms
3. **Retry utility:** `core/utils/retry.py` — Add exponential backoff option
4. **Metrics:** Extend ResourceMonitor with rate limit metrics

### Key Files to Modify
1. `core/rate_limiter.py` — New: PlatformRateLimiter class
2. `core/utils/retry.py` — Add exponential backoff option
3. `infrastructure/health_runtime.py` — Add rate limit metrics
4. Platform clients — Integrate PlatformRateLimiter

</code_context>

<specifics>
## Specific Ideas

### Phase 4 Deliverables
1. **RATE-01:** Per-platform rate limits (PlatformRateLimiter class)
2. **RATE-02:** Per-provider rate limits (extend to SMS/captcha)
3. **RATE-03:** Adaptive rate limiting (exponential backoff, circuit breaker extension)
4. **RATE-04:** Rate limit metrics and monitoring (RateLimitMetrics, /api/rate-limits)

### Key Changes
- `core/rate_limiter.py` — New: PlatformRateLimiter, RateLimitMetrics
- `core/utils/retry.py` — Add exponential backoff option
- `infrastructure/health_runtime.py` — Add rate limit metrics
- Platform clients — Integrate PlatformRateLimiter
- `api/health.py` — Add GET /api/rate-limits endpoint

### Success Criteria
1. Per-platform rate limits enforced
2. Per-provider rate limits extended to SMS/captcha
3. Adaptive backoff works for critical paths
4. Rate limit metrics available via API

</specifics>

<deferred>
## Deferred Ideas

- **Redis-based rate limiting** — Requires distributed system (v2)
- **API middleware rate limiting** — Separate security milestone
- **Per-user rate limiting** — Requires auth system enhancement

</deferred>
