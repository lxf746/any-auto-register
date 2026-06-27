# Phase 1: PostgreSQL Migration - Context

**Gathered:** 2026-06-27
**Status:** Ready for planning
**Mode:** Codebase analysis + requirements

<domain>
## Phase Boundary

Перейти с SQLite на PostgreSQL для production. SQLite остаётся для development.

</domain>

<decisions>
## Implementation Decisions

### 1. PostgreSQL Driver Selection
| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| psycopg2 (sync) | Stable, widely used, good SQLAlchemy support | Synchronous, blocks event loop | ❌ Not for async |
| asyncpg (async) | Fastest PostgreSQL driver, native async | Requires async SQLAlchemy | ✅ Recommended |
| psycopg (v3, async) | Newer, Python-native, async support | Less mature than asyncpg | ⚠️ Alternative |

**Decision:** Use asyncpg with SQLAlchemy async engine for main app. Keep sync engine for migrations.

### 2. Database Scope
| Database | Tables | Migration Complexity | Decision |
|----------|--------|---------------------|----------|
| Main app (account_manager.db) | 13 tables | High (SQLite-specific migrations) | ✅ Migrate |
| Customer portal (customer_portal.db) | 17 tables | Low (clean models) | ⏳ Separate milestone |

**Decision:** Migrate main app DB only. Portal is separate app.

### 3. Connection String Format
| Format | Example | Use Case |
|--------|---------|----------|
| `postgresql+asyncpg://user:pass@host:port/db` | `postgresql+asyncpg://postgres:secret@localhost:5432/accounts` | Async (main app) |
| `postgresql+psycopg2://user:pass@host:port/db` | `postgresql+psycopg2://postgres:secret@localhost:5432/accounts` | Sync (migrations) |
| `postgresql://user:pass@host:port/db` | `postgresql://postgres:secret@localhost:5432/accounts` | Shorthand (auto-selects driver) |

**Decision:** Use `postgresql+asyncpg://` for explicit async driver selection.

### 4. Migration Strategy
| Approach | Pros | Cons | Recommendation |
|----------|------|------|----------------|
| Alembic | Industry standard, tracks versions, rollback support | Adds dependency, requires setup | ✅ Recommended |
| Custom (current) | No dependencies, full control | SQLite-specific, hard to maintain | ❌ Replace |
| Manual SQL | Simple, explicit | Error-prone, no versioning | ❌ Not recommended |

**Decision:** Replace custom migrations with Alembic for proper version control.

### 5. Fallback Strategy
| Scenario | Behavior | Implementation |
|----------|----------|----------------|
| PostgreSQL available | Use PostgreSQL | Check connection string prefix |
| PostgreSQL unavailable | Fall back to SQLite | Try connection, catch OperationalError |
| Development mode | Always SQLite | `DEV_MODE=true` env var |

**Decision:** Auto-detect based on connection string. Support `--dev` flag for forced SQLite.

</decisions>

<code_context>
## Existing Code Insights

### Current Database Architecture
- **Engine:** `/home/vitaly/projects/any-auto-register/core/db/engine.py:22-28` — SQLite-only, sync engine
- **Models:** `/home/vitaly/projects/any-auto-register/core/db/models.py` — 13 SQLModel tables
- **Migrations:** `/home/vitaly/projects/any-auto-register/core/db/migrations.py` — Custom, SQLite-specific (PRAGMA foreign_keys)
- **Encryption:** `/home/vitaly/projects/any-auto-register/core/db/encryption.py` — Fernet encryption for passwords

### SQLite-Specific Code to Refactor
1. `migrations.py:131` — `PRAGMA foreign_keys=OFF/ON` (SQLite-only)
2. `migrations.py:134-153` — Raw `CREATE TABLE`, `DROP TABLE`, `ALTER TABLE RENAME` (SQLite table rebuild pattern)
3. `engine.py:72` — `exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")` (f-string interpolation)

### Session Usage Pattern
- All services use `with Session(engine) as session:` directly
- No FastAPI dependency injection for main app
- Customer portal uses `Depends(get_db_session)` pattern

### Test Infrastructure
- `tests/conftest.py:12-27` — Creates temp SQLite file, patches engine with `check_same_thread=False`
- Tests rely on SQLite-specific behavior

</code_context>

<specifics>
## Specific Ideas

### Phase 1 Deliverables
1. **PG-01:** Add `asyncpg` to requirements.txt
2. **PG-02:** Create async SQLAlchemy engine for PostgreSQL
3. **PG-03:** Setup Alembic with PostgreSQL migration support
4. **PG-04:** Update env var handling for `ACCOUNT_MANAGER_DATABASE_URL`
5. **PG-05:** Auto-detect PostgreSQL vs SQLite based on URL prefix

### Key Changes
- `core/db/engine.py` — Add async engine, connection pooling config
- `alembic.ini` + `alembic/` — New migration framework
- `requirements.txt` — Add asyncpg, alembic
- `tests/conftest.py` — Support both SQLite and PostgreSQL test databases

### Migration Approach
1. Setup Alembic with PostgreSQL support
2. Generate initial migration from current models
3. Keep SQLite fallback for development
4. Update all session creation to use new engine

</specifics>

<deferred>
## Deferred Ideas

- **Customer Portal migration** — Separate app, separate milestone
- **Connection pooling** — Phase 2 (POOL-01)
- **Async session management** — Phase 2 (POOL-02)
- **Concurrent registration** — Phase 3 (CONC-01)

</deferred>
