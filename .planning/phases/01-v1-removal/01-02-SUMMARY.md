---
phase: 01-v1-removal
plan: 02
subsystem: api
tags: [migration, auth, cleanup, removal]
dependency_graph:
  requires: [01-01]
  provides: []
  affects: [api/v2/auth.py, api/v2/router.py, api/v2/deps.py, api/v2/ws.py, core/auth.py, main.py]
tech_stack:
  added: []
  patterns: []
key_files:
  created: [api/v2/auth.py]
  modified: [api/v2/router.py, api/v2/deps.py, api/v2/ws.py, core/auth.py, main.py]
  deleted: [api/auth.py, api/accounts.py, api/account_checks.py, api/actions.py, api/config.py, api/health.py, api/lifecycle.py, api/platform_capabilities.py, api/platforms.py, api/provider_definitions.py, api/provider_settings.py, api/proxies.py, api/sms.py, api/stats.py, api/system.py, api/task_commands.py, api/task_logs.py, api/tasks.py, api/__init__.py]
decisions:
  - "Moved AccountsService instantiation into v2 router to decouple from v1 api.accounts module"
metrics:
  duration: "3m"
  completed: "2026-06-27"
  tasks_completed: 3
  files_changed: 24
  files_deleted: 19
status: complete
---

# Phase 01 Plan 02: Migrate auth to v2 and remove v1 API Summary

Migrated auth functions (create_session, validate_session, destroy_session, _check_rate_limit, _sessions) to api/v2/auth.py. Updated all v2 modules and core/auth.py to import from api.v2.auth. Removed all v1 API files (19 files). Cleaned main.py of v1 router imports and include_router calls.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed v2 router dependency on api.accounts.service**
- **Found during:** Task 2 execution
- **Issue:** api/v2/router.py imported `from api.accounts import service` which was deleted
- **Fix:** Changed to `from application.accounts import AccountsService` and instantiated service directly in v2 router
- **Files modified:** api/v2/router.py
- **Commit:** 1d8c61d

## Known Stubs

None.

## Threat Flags

None — auth migration preserves in-memory session semantics exactly as before.

## Self-Check: PASSED

- [x] `test ! -f api/auth.py && test ! -f api/accounts.py` — v1 files removed
- [x] `python3 -c "from main import app"` — app imports OK
- [x] `python3 -c "from api.v2.auth import create_session, validate_session, _check_rate_limit"` — v2 auth functions work
- [x] `! grep -r "from api.(auth|accounts)" --include="*.py" . | grep -v "api/v2/" | grep -v "__pycache__"` — no v1 references outside v2
- [x] `grep -c "v2_router" main.py` — v2 router connected
