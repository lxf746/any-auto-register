# Requirements: Any Auto Register

**Defined:** 2026-06-27
**Core Value:** Автоматическая регистрация аккаунтов должна работать надёжно и безопасно

## v1.6 Requirements

### PostgreSQL Migration

- [ ] **PG-01**: PostgreSQL driver (asyncpg/psycopg2) integration
- [ ] **PG-02**: SQLAlchemy dialect for PostgreSQL
- [ ] **PG-03**: Database migration scripts (SQLite → PostgreSQL)
- [x] **PG-04**: Connection string configuration (env vars)
- [x] **PG-05**: Fallback to SQLite for development

### Connection Pooling

- [ ] **POOL-01**: Database connection pooling (SQLAlchemy pool)
- [ ] **POOL-02**: HTTP session pooling (aiohttp/requests adapter)
- [ ] **POOL-03**: Browser instance pooling (Playwright contexts)
- [ ] **POOL-04**: Pool monitoring and metrics

### Concurrent Registration

- [ ] **CONC-01**: Parallel task execution across platforms
- [ ] **CONC-02**: Worker pool for concurrent registrations
- [ ] **CONC-03**: Task prioritization and scheduling
- [ ] **CONC-04**: Resource-aware concurrency limits

### Rate Limiting

- [ ] **RATE-01**: Per-platform rate limits
- [ ] **RATE-02**: Per-provider rate limits (SMS, email, captcha)
- [ ] **RATE-03**: Adaptive rate limiting (backoff on errors)
- [ ] **RATE-04**: Rate limit metrics and monitoring

## v2 Requirements

### Scaling

- **SCAL-01**: Horizontal scaling (multiple workers)
- **SCAL-02**: Distributed task queue (Celery/RQ)
- **SCAL-03**: Redis for caching and rate limiting

## Out of Scope

| Feature | Reason |
|---------|--------|
| Новые платформы | Отдельный milestone |
| Тесты | Отдельный milestone |
| Мониторинг | Отдельный milestone |
| Kubernetes/Docker | Инфраструктурный milestone |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PG-01 | Phase 1 | Pending |
| PG-02 | Phase 1 | Pending |
| PG-03 | Phase 1 | Pending |
| PG-04 | Phase 1 | Complete |
| PG-05 | Phase 1 | Complete |
| POOL-01 | Phase 2 | Pending |
| POOL-02 | Phase 2 | Pending |
| POOL-03 | Phase 2 | Pending |
| POOL-04 | Phase 2 | Pending |
| CONC-01 | Phase 3 | Pending |
| CONC-02 | Phase 3 | Pending |
| CONC-03 | Phase 3 | Pending |
| CONC-04 | Phase 3 | Pending |
| RATE-01 | Phase 4 | Pending |
| RATE-02 | Phase 4 | Pending |
| RATE-03 | Phase 4 | Pending |
| RATE-04 | Phase 4 | Pending |

**Coverage:**
- v1.6 requirements: 17 total
- Mapped to phases: 17
- Unmapped: 0 ✓

---
*Requirements defined: 2026-06-27*
*Last updated: 2026-06-27 after initial definition*
