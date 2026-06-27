---
phase: 03-account-endpoints
subsystem: api
tags: [api, accounts, crud, export, checks, v2]
dependency_graph:
  requires: [02-01]
  provides: [EP-01, EP-02, EP-03, EP-04]
  affects: [api/v2/accounts.py, api/v2/router.py]
tech_stack:
  added: [streamingresponse]
  patterns: [fastapi-router, pydantic-models, streaming-response, export-artifact]
key_files:
  created: [api/v2/accounts.py, tests/test_v2_accounts.py, tests/test_v2_account_exports.py, tests/test_v2_account_checks.py]
  modified: [api/v2/router.py]
decisions:
  - "Route ordering: static routes before parameterized to prevent FastAPI path shadowing"
  - "Delete endpoint checks repository return value and returns 404 for missing accounts"
  - "Export endpoints use StreamingResponse; data endpoints use ApiResponse envelope"
metrics:
  duration: 17m
  completed: "2026-06-27"
  tasks: 4
  files_created: 3
  files_modified: 2
status: complete
---

# Phase 3: Account Endpoints Summary

Complete v2 Account API layer — CRUD, stats, import, 6 export formats, and async check endpoints.

## What Was Built

### api/v2/accounts.py (14 endpoints total)

**CRUD (4):**
- `POST /api/v2/accounts/` — create account
- `GET /api/v2/accounts/{id}` — get account by ID
- `PATCH /api/v2/accounts/{id}` — update account
- `DELETE /api/v2/accounts/{id}` — delete account (404 for missing)

**Data (2):**
- `GET /api/v2/accounts/stats` — account statistics
- `POST /api/v2/accounts/import` — import from text lines

**Export (6):**
- `POST /api/v2/accounts/export/csv` — CSV download
- `POST /api/v2/accounts/export/json` — JSON download
- `POST /api/v2/accounts/export/sub2api` — Sub2API format
- `POST /api/v2/accounts/export/cpa` — CPA token format
- `POST /api/v2/accounts/export/kiro-go` — Kiro-Go config
- `POST /api/v2/accounts/export/any2api` — Any2API admin config

**Checks (2):**
- `POST /api/v2/accounts/check-all` — async check all accounts
- `POST /api/v2/accounts/check-one/{id}` — async check one account

### api/v2/router.py
- Added `accounts_router` import and `include_router`

### Test Files (22 tests total)
- `tests/test_v2_accounts.py` — 12 tests (CRUD, stats, import)
- `tests/test_v2_account_exports.py` — 6 tests (all export formats)
- `tests/test_v2_account_checks.py` — 4 tests (check-all, check-one)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed delete endpoint returning 200 for missing accounts**
- **Found during:** Plan 01, Task 2
- **Issue:** `DELETE /api/v2/accounts/99999` returned 200 instead of 404
- **Fix:** Added `if not result.get("ok"): raise HTTPException(404, "Account not found")`
- **Files modified:** `api/v2/accounts.py`
- **Commit:** 5ce2fff

**2. [Rule 1 - Bug] Fixed route ordering — stats/import shadowed by /{account_id}**
- **Found during:** Plan 01, Task 2
- **Issue:** `GET /api/v2/accounts/stats` returned 422 because FastAPI matched `stats` as `{account_id}` int
- **Fix:** Moved static routes before parameterized routes
- **Files modified:** `api/v2/accounts.py`
- **Commit:** 5ce2fff

## Commits

| Hash | Message |
|------|---------|
| 39b0d8c | feat(03-01): add Account CRUD, stats, and import endpoints to v2 |
| 5ce2fff | test(03-01): register accounts router, add 12 v2 integration tests |
| 191f611 | feat(03-02): add 6 export endpoints and 2 check endpoints to v2 |
| 7430fd5 | test(03-02): add export and check integration tests |

## Test Results

- 22/22 tests pass
- All endpoints return correct response format (ApiResponse or StreamingResponse)
- App starts without import errors

## Known Stubs

None — all endpoints are fully wired to existing services.

## Threat Flags

None — all endpoints use existing auth middleware and service layer. Export endpoints are intentional data exposure (T-03-04 accepted).
