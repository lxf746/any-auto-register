# Project State

## Current Position

Phase: 02-connection-pooling
Plan: 01 (complete)
Status: In Progress
Last activity: 2026-06-27 — Plan 02-01 (Database Connection Pooling) complete

## Milestone

**v1.6 Scaling & Performance**

Goal: Подготовить систему к production нагрузке — PostgreSQL, connection pooling, параллельная регистрация, rate limiting

## Progress

| Metric | Value |
|--------|-------|
| Current phase | 02-connection-pooling |
| Plans complete | 1/4 (Phase 2) |
| Tasks complete | 6/6 (Phase 1: 4, Phase 2 Plan 1: 2) |

## Context

### Decisions

- PostgreSQL вместо SQLite
- Connection pooling для БД и HTTP
- Параллельная регистрация
- Rate limiting для провайдеров
- Engine auto-detection: URL prefix → PostgreSQL or SQLite (01-02)
- Sync engine normalizes asyncpg → psycopg2 for backward compat (01-02)
- Alembic env var pattern: ACCOUNT_MANAGER_DATABASE_URL with SQLite fallback (01-01)
- Initial migration covers all 13 SQLModel tables (01-01)
- QueuePool config applied uniformly to all DB types including SQLite (02-01)
- Dual dispose paths: lifecycle_manager.stop() + main.py lifespan for defense-in-depth (02-01)

### Blockers

- Нет

### Todos

- Нет
