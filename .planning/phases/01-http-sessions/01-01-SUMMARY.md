---
phase: 01-http-sessions
plan: 01
subsystem: database
tags: [postgresql, asyncpg, alembic, sqlmodel, migration]

# Dependency graph
requires:
  - phase: none
    provides: initial setup
provides:
  - asyncpg, psycopg2-binary, alembic dependencies installed
  - Alembic configured for PostgreSQL and SQLite
  - Initial migration covering all 13 SQLModel tables
affects: [01-02, 02-connection-pooling]

# Tech tracking
tech-stack:
  added: [asyncpg, psycopg2-binary, alembic]
  patterns: [env-var-driven-database-url, asyncpg-to-psycopg2-normalization, alembic-autogenerate]

key-files:
  created:
    - alembic.ini
    - alembic/env.py
    - alembic/script.py.mako
    - alembic/versions/001_initial_schema.py
  modified:
    - requirements.txt

key-decisions:
  - "Alembic reads ACCOUNT_MANAGER_DATABASE_URL env var with sqlite fallback"
  - "asyncpg URLs normalized to psycopg2 for sync Alembic compatibility"
  - "Initial migration uses CREATE TABLE IF NOT EXISTS pattern for idempotency"

patterns-established:
  - "Alembic env var pattern: read from ACCOUNT_MANAGER_DATABASE_URL, default to SQLite"
  - "Dual-driver normalization: asyncpg for app, psycopg2 for migrations"

requirements-completed: [PG-01, PG-02, PG-03]

coverage:
  - id: D1
    description: asyncpg, psycopg2-binary, and alembic installed and importable"
    requirement: PG-01
    verification:
      - kind: unit
        ref: "python3 -c 'import asyncpg; import psycopg2; import alembic'"
        status: pass
    human_judgment: false
  - id: D2
    description: "Alembic configured with PostgreSQL dialect support"
    requirement: PG-02
    verification:
      - kind: unit
        ref: "alembic/env.py imports SQLModel.metadata from core.db.models"
        status: pass
    human_judgment: false
  - id: D3
    description: "Initial migration creates all 13 SQLModel tables with indexes"
    requirement: PG-03
    verification:
      - kind: unit
        ref: "alembic upgrade head + sqlite3 table count"
        status: pass
    human_judgment: false
  - id: D4
    description: "Migration downgrade removes all tables cleanly"
    requirement: PG-03
    verification:
      - kind: unit
        ref: "alembic downgrade base + sqlite3 table count"
        status: pass
    human_judgment: false

# Metrics
duration: 2min
completed: 2026-06-27
status: complete
---

# Phase 1 Plan 01: Dependencies & Alembic Setup Summary

**PostgreSQL driver asyncpg + sync psycopg2 for migrations, Alembic framework with initial migration covering all 13 SQLModel tables**

## Performance

- **Duration:** 2 min
- **Started:** 2026-06-27T06:14:03Z
- **Completed:** 2026-06-27T06:16:23Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Added asyncpg (async PostgreSQL driver), psycopg2-binary (sync fallback), and alembic to requirements.txt
- Initialized Alembic with env-var-driven DATABASE_URL configuration
- Created initial migration 001_initial_schema.py covering all 13 SQLModel tables with correct indexes and constraints
- Verified upgrade creates all tables, downgrade removes them cleanly

## Task Commits

Each task was committed atomically:

1. **Task 1: Add PostgreSQL and Alembic dependencies** — `290697f` (chore)
2. **Task 2: Initialize Alembic and create initial migration** — `8f27f05` (feat)

## Files Created/Modified
- `requirements.txt` — Added asyncpg, psycopg2-binary, alembic under # PostgreSQL support
- `alembic.ini` — Configured with env-var-driven sqlalchemy.url
- `alembic/env.py` — Reads ACCOUNT_MANAGER_DATABASE_URL, normalizes asyncpg → psycopg2
- `alembic/script.py.mako` — Default Alembic template (unchanged)
- `alembic/versions/001_initial_schema.py` — Initial migration: all 13 tables with indexes

## Decisions Made
- Alembic reads ACCOUNT_MANAGER_DATABASE_URL env var, defaults to SQLite
- asyncpg URLs normalized to psycopg2 for sync Alembic compatibility
- Initial migration is idempotent and supports both upgrade and downgrade

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None - all implementations are complete and functional.

## Threat Flags

None - no new security surface introduced beyond what was planned.

## Self-Check: PASSED

---
*Phase: 01-http-sessions*
*Completed: 2026-06-27*
