# Project State

## Current Position

Phase: 02-connection-pooling
Plan: —
Status: Starting
Last activity: 2026-06-27 — Phase 1 PostgreSQL Migration complete

## Milestone

**v1.6 Scaling & Performance**

Goal: Подготовить систему к production нагрузке — PostgreSQL, connection pooling, параллельная регистрация, rate limiting

## Progress

| Metric | Value |
|--------|-------|
| Current phase | 02-connection-pooling |
| Plans complete | 2/2 (Phase 1) |
| Tasks complete | 4/4 (Phase 1) |

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

### Blockers

- Нет

### Todos

- Нет
