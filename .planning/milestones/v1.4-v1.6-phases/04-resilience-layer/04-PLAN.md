# Phase 4: Resilience Layer - Plan

**Created:** 2026-06-26
**Status:** Ready for execution

## Tasks

### T4.1: Create resilience components
- Create `core/mailbox/resilience.py` with:
  - `HealthCheck` class — pre-flight health check with TTL cache
  - `CircuitBreaker` class — closed/open/half-open states
  - `RateLimiter` class — per-provider rate limiting
  - `EmailDedup` class — email deduplication cache

### T4.2: Integrate health checks
- Add health check before first use in create_mailbox()
- Cache health check results with configurable TTL

### T4.3: Integrate circuit breaker
- Wrap each provider instance with CircuitBreaker
- Configurable failure threshold and recovery timeout

### T4.4: Integrate rate limiting
- Add RateLimiter to each provider
- Configurable requests per minute

### T4.5: Integrate email dedup
- Add EmailDedup to FallbackMailbox.get_email()
- Prevent duplicate email creation for same address

### T4.6: Add resilience config
- Add resilience fields to MailboxConfig base dataclass
- health_check_enabled, circuit_breaker_enabled, rate_limit_rpm, etc.

### T4.7: Verify and cleanup
- Verify all modules parse correctly

## Success Criteria

1. Pre-flight health check выполняется перед первым использованием ✓
2. Circuit breaker переключается между closed/open/half-open ✓
3. Health check результаты кэшируются с TTL ✓
4. Email dedup не создаёт дубли для одного адреса ✓
5. Per-provider rate limits конфигурируются ✓

## Dependencies

Phase 1 (Module Split) — Complete
Phase 2 (Unified Registry) — Complete
Phase 3 (Typed Config) — Complete

## Risk

Medium — adding new behavior, needs careful integration.
