---
phase: 03-account-endpoints
plan: 01
subsystem: api
tags: [api, accounts, crud, v2]
dependency_graph:
  requires: [02-01]
  provides: [EP-01, EP-03]
  affects: [api/v2/accounts.py, api/v2/router.py]
tech_stack:
  added: []
  patterns: [fastapi-router, pydantic-models, streaming-response]
key_files:
  created: [api/v2/accounts.py, tests/test_v2_accounts.py]
  modified: [api/v2/router.py]
decisions:
  - "Route ordering: stats/import defined before /{account_id} to prevent path parameter shadowing"
  - "Delete endpoint checks repository return value and returns 404 for missing accounts"
metrics:
  duration: 7m
  completed: "2026-06-27"
  tasks: 2
  files_created: 2
  files_modified: 1
status: complete
---

# Phase 3 Plan 1: Account CRUD, stats, import Summary

Full Account CRUD, stats, and import endpoints working in v2 API layer.

## What Was Built

- `api/v2/accounts.py` — New file with 6 endpoints:
  - `POST /api/v2/accounts/` — create account
  - `GET /api/v2/accounts/{id}` — get account by ID
  - `PATCH /api/v2/accounts/{id}` — update account
  - `DELETE /api/v2/accounts/{id}` — delete account (with 404 for missing)
  - `GET /api/v2/accounts/stats` — account statistics
  - `POST /api/v2/accounts/import` — import accounts from text lines
- `api/v2/router.py` — Updated to include accounts_router
- `tests/test_v2_accounts.py` — 12 integration tests covering all endpoints

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed delete endpoint returning 200 for missing accounts**
- **Found during:** Task 2
- **Issue:** `DELETE /api/v2/accounts/99999` returned 200 instead of 404. The repository's `delete()` returns `False` for missing accounts, but the endpoint ignored the return value.
- **Fix:** Added check `if not result.get("ok"): raise HTTPException(404, "Account not found")`
- **Files modified:** `api/v2/accounts.py`
- **Commit:** 5ce2fff

**2. [Rule 1 - Bug] Fixed route ordering — stats/import shadowed by /{account_id}**
- **Found during:** Task 2
- **Issue:** `GET /api/v2/accounts/stats` returned 422 because FastAPI matched `stats` as `{account_id}` int parameter.
- **Fix:** Moved stats and import route definitions before `/{account_id}` routes.
- **Files modified:** `api/v2/accounts.py`
- **Commit:** 5ce2fff

## Key Decisions

- **Route ordering matters:** Static routes (`/stats`, `/import`, `/export/*`, `/check-*`) must be defined before parameterized routes (`/{account_id}`) to avoid FastAPI path shadowing.
- **Delete 404 check:** The service layer returns `{"ok": False}` for missing accounts; the API layer translates this to HTTP 404.
- **List endpoint kept in router.py:** The existing `GET /api/v2/accounts` list endpoint remains in router.py per plan instruction — no unnecessary churn.

## Test Results

- 12/12 tests pass
- All endpoints return v2 ApiResponse envelope
- App starts without import errors
