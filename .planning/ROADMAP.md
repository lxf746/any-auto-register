# Roadmap: v1.6 Scaling & Performance

**Created:** 2026-06-27
**Phases:** 4
**Requirements:** 17 mapped

## Phase 1: PostgreSQL Migration

**Goal:** Перейти с SQLite на PostgreSQL для production

**Requirements:**
- PG-01: PostgreSQL driver integration
- PG-02: SQLAlchemy dialect
- PG-03: Migration scripts
- PG-04: Connection string configuration
- PG-05: Fallback to SQLite

**Success Criteria:**
1. PostgreSQL работает как основная БД
2. SQLite остаётся для development
3. Миграция данных корректна
4. Все тесты проходят

**Plans:** 2 plans
- [ ] 01-01-PLAN.md — Dependencies & Alembic setup (asyncpg, psycopg2, alembic, initial migration)
- [x] 01-02-PLAN.md — Engine refactoring & dual-database support (auto-detection, tests, docker-compose)

---

## Phase 2: Connection Pooling

**Goal:** Оптимизировать использование соединений

**Requirements:**
- POOL-01: Database connection pooling
- POOL-02: HTTP session pooling
- POOL-03: Browser instance pooling
- POOL-04: Pool monitoring

**Success Criteria:**
1. Connection pooling работает для БД
2. HTTP сессии переиспользуются
3. Browser contexts пулятся
4. Мониторинг пулов доступен

---

## Phase 3: Concurrent Registration

**Goal:** Параллельная регистрация на多个 платформах

**Requirements:**
- CONC-01: Parallel task execution
- CONC-02: Worker pool
- CONC-03: Task prioritization
- CONC-04: Resource-aware limits

**Success Criteria:**
1. Параллельная регистрация работает
2. Worker pool управляет потоками
3. Приоритеты задач работают
4. Лимиты ресурсов соблюдаются

---

## Phase 4: Rate Limiting

**Goal:** Контроль скорости запросов к провайдерам

**Requirements:**
- RATE-01: Per-platform rate limits
- RATE-02: Per-provider rate limits
- RATE-03: Adaptive rate limiting
- RATE-04: Rate limit metrics

**Success Criteria:**
1. Rate limits работают для платформ
2. Rate limits работают для провайдеров
3. Адаптивный backoff работает
4. Метрики rate limits доступны
