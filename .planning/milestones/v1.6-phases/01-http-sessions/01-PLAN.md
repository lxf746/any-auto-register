---
phase: 01-http-sessions
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - requirements.txt
  - alembic.ini
  - alembic/env.py
  - alembic/script.py.mako
  - alembic/versions/001_initial_schema.py
autonomous: true
requirements:
  - PG-01
  - PG-02
  - PG-03
  - PG-04
must_haves:
  truths:
    - PostgreSQL driver asyncpg is installed and importable
    - Alembic is installed and configured with PostgreSQL dialect
    - Initial migration script exists and can generate all 13 SQLModel tables
    - DATABASE_URL env var is read for PostgreSQL connection string
    - alembic.ini points to correct models and migration paths
  artifacts:
    - requirements.txt (with asyncpg, alembic, psycopg2-binary)
    - alembic.ini
    - alembic/env.py
    - alembic/script.py.mako
    - alembic/versions/001_initial_schema.py
  key_links:
    - alembic/env.py imports models from core.db.models
    - alembic.ini sqlalchemy.url reads ACCOUNT_MANAGER_DATABASE_URL
---

<objective>
Add PostgreSQL driver dependencies and initialize Alembic migration framework.

Purpose: Establish the foundation for PostgreSQL support — install asyncpg for async driver, psycopg2 for sync fallback, and Alembic for schema versioning. Create initial migration from current SQLModel definitions.
Output: Updated requirements.txt, fully configured Alembic setup, initial migration script.
</objective>

<execution_context>
@/home/vitaly/.config/opencode/gsd-core/workflows/execute-plan.md
@/home/vitaly/.config/opencode/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/01-http-sessions/01-CONTEXT.md

@requirements.txt
@core/db/models.py
@core/db/engine.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add PostgreSQL and Alembic dependencies</name>
  <files>requirements.txt</files>
  <read_first>
    - requirements.txt (current dependencies to avoid duplicates)
  </read_first>
  <action>
Add the following packages to requirements.txt after the existing `# Encryption for password-at-rest` section:

- `asyncpg>=0.29.0` — async PostgreSQL driver for SQLAlchemy async engine (per D-01)
- `psycopg2-binary>=2.9.9` — sync PostgreSQL driver for Alembic migrations and sync engine fallback
- `alembic>=1.13.0` — schema migration framework replacing custom migrations (per D-04)

Place them under a new comment section `# PostgreSQL support`. Do NOT remove or modify any existing entries.
  </action>
  <verify>
    <automated>pip install -r requirements.txt 2>&1 | tail -5 && python -c "import asyncpg; import psycopg2; import alembic; print('OK: asyncpg', asyncpg.__version__, 'psycopg2', psycopg2.__version__, 'alembic', alembic.__version__)"</automated>
  </verify>
  <acceptance_criteria>
    - requirements.txt contains `asyncpg>=0.29.0`, `psycopg2-binary>=2.9.9`, `alembic>=1.13.0`
    - `python -c "import asyncpg; import psycopg2; import alembic"` exits 0
    - No existing entries in requirements.txt were modified or removed
  </acceptance_criteria>
  <done>asyncpg, psycopg2-binary, and alembic are installed and importable</done>
</task>

<task type="auto">
  <name>Task 2: Initialize Alembic and create initial PostgreSQL migration</name>
  <files>alembic.ini, alembic/env.py, alembic/script.py.mako, alembic/versions/001_initial_schema.py</files>
  <read_first>
    - core/db/models.py (all 13 SQLModel table definitions — source of truth for migration)
    - core/db/engine.py (DATABASE_URL env var name, engine creation pattern)
    - core/db/__init__.py (exports list — what Alembic env.py must import)
  </read_first>
  <action>
Run `alembic init alembic` to scaffold the directory structure, then customize:

1. **alembic.ini**: Set `sqlalchemy.url = %(DATABASE_URL)s` and add `[keys]` section with `DATABASE_URL` key. The env.py will override this from env var at runtime.

2. **alembic/env.py**: Configure to:
   - Import `target_metadata` from `core.db.models.SQLModel.metadata`
   - Read `ACCOUNT_MANAGER_DATABASE_URL` env var (matching existing convention in engine.py line 27)
   - Default to `sqlite:///account_manager.db` if env var is unset
   - For PostgreSQL URLs, ensure `postgresql+asyncpg://` prefix is normalized to `postgresql+psycopg2://` for Alembic (sync driver required)
   - Call `SQLModel.metadata` as target_metadata for autogenerate support

3. **alembic/versions/001_initial_schema.py**: Create initial migration that:
   - Creates all 13 tables from models.py: accounts, account_overviews, account_credentials, provider_accounts, provider_resources, provider_definitions, provider_settings, platform_capability_overrides, task_logs, tasks, task_events, proxies, schema_version
   - Includes all indexes (platform, email, provider_type, etc.)
   - Includes UniqueConstraints (provider_definitions, provider_settings, platform_capability_overrides)
   - Uses `CREATE TABLE IF NOT EXISTS` idempotency pattern
   - Downgrade drops all tables

4. **alembic/script.py.mako**: Keep default template, no changes needed.

Do NOT modify core/db/engine.py in this plan — that is handled in Plan 02.
  </action>
  <verify>
    <automated>cd /home/vitaly/projects/any-auto-register && python -m alembic upgrade head 2>&1 | tail -3 && python -c "
import sqlite3, os
db = sqlite3.connect('account_manager.db')
tables = {r[0] for r in db.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()}
expected = {'accounts','account_overviews','account_credentials','provider_accounts','provider_resources','provider_definitions','provider_settings','platform_capability_overrides','task_logs','tasks','task_events','proxies','schema_version','alembic_version'}
missing = expected - tables
assert not missing, f'Missing tables: {missing}'
print(f'OK: {len(tables)} tables created')
db.close()
"</automated>
  </verify>
  <acceptance_criteria>
    - `alembic.ini` exists with `sqlalchemy.url` configured
    - `alembic/env.py` exists and imports `SQLModel.metadata` from `core.db.models`
    - `alembic/env.py` reads `ACCOUNT_MANAGER_DATABASE_URL` env var
    - `alembic/versions/001_initial_schema.py` exists with upgrade() creating all 13 tables
    - Running `alembic upgrade head` on a fresh SQLite database creates all expected tables
    - Running `alembic downgrade base` drops all tables
    - The `schema_version` table (custom migration tracking) is included in the schema
  </acceptance_criteria>
  <done>Alembic is fully configured, initial migration creates all 13 SQLModel tables, downgrade removes them</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| env vars → engine | DATABASE_URL contains credentials; must not be logged or exposed in error messages |
| npm/pip installs | New dependencies (asyncpg, psycopg2-binary, alembic) must be legitimate packages |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-1-01 | Information Disclosure | alembic/env.py | medium | mitigate | Ensure DATABASE_URL with credentials is never logged; use `repr()` or redact in debug output |
| T-1-02 | Tampering | pip installs (asyncpg, psycopg2-binary, alembic) | high | mitigate | Verify package names against PyPI; these are well-known packages with millions of downloads. Pin versions in requirements.txt |
| T-1-03 | Elevation of Privilege | PostgreSQL connection | medium | mitigate | Use least-privilege database user; do not use superuser in production. Alembic migrations run with app credentials |
</threat_model>

<verification>
1. `pip install -r requirements.txt` succeeds without errors
2. `python -c "import asyncpg; import psycopg2; import alembic"` exits 0
3. `alembic upgrade head` creates all 13 tables in SQLite
4. `alembic downgrade base` removes all tables
5. `alembic revision --autogenerate -m "test"` generates a no-op revision (schema matches models)
</verification>

<success_criteria>
- All 3 new packages installed and importable
- Alembic configured with PostgreSQL dialect support
- Initial migration covers all 13 SQLModel tables
- Migration is idempotent and reversible
</success_criteria>

<output>
Create `.planning/phases/01-http-sessions/01-01-SUMMARY.md` when done
</output>
