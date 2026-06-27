---
phase: 03-account-endpoints
plan: 02
subsystem: api
tags: [api, accounts, export, checks, v2]
dependency_graph:
  requires: [03-01]
  provides: [EP-02, EP-04]
  affects: [api/v2/accounts.py]
tech_stack:
  added: [streamingresponse]
  patterns: [streaming-response, export-artifact]
key_files:
  created: [tests/test_v2_account_exports.py, tests/test_v2_account_checks.py]
  modified: [api/v2/accounts.py]
decisions:
  - "Export endpoints use StreamingResponse with Content-Disposition header for file downloads"
  - "Check endpoints return ApiResponse envelope with task dict"
metrics:
  duration: 10m
  completed: "2026-06-27"
  tasks: 2
  files_created: 2
  files_modified: 1
status: complete
---

# Phase 3 Plan 2: Account Exports + Checks Summary

6 export formats (CSV, JSON, sub2api, CPA, kiro-go, any2api) and 2 check endpoints (check-all, check-one) working in v2 API layer.

## What Was Built

Extended `api/v2/accounts.py` with 8 new endpoints:
- `POST /api/v2/accounts/export/csv` — CSV file download
- `POST /api/v2/accounts/export/json` — JSON file download
- `POST /api/v2/accounts/export/sub2api` — Sub2API format (single JSON or ZIP)
- `POST /api/v2/accounts/export/cpa` — CPA token format (single JSON or ZIP)
- `POST /api/v2/accounts/export/kiro-go` — Kiro-Go CLI Proxy config
- `POST /api/v2/accounts/export/any2api` — Any2API admin config (multi-platform)
- `POST /api/v2/accounts/check-all` — trigger async check for all accounts
- `POST /api/v2/accounts/check-one/{id}` — trigger async check for one account

Test files:
- `tests/test_v2_account_exports.py` — 6 tests covering all export formats
- `tests/test_v2_account_checks.py` — 4 tests covering check-all and check-one

## Deviations from Plan

None — plan executed exactly as written.

## Key Decisions

- **StreamingResponse for exports:** File downloads use `StreamingResponse` with `Content-Disposition` header, not `ApiResponse` envelope — this is correct for binary/CSV/JSON file downloads.
- **ExportArtifacts pattern:** The `_stream_artifact()` helper converts `ExportArtifact` (from `AccountExportsService`) to `StreamingResponse`, handling both `str` and `BytesIO` content types.
- **Check endpoints return task dict:** Both check-all and check-one return the task dict from the service layer inside the `ApiResponse` envelope.

## Test Results

- 10/10 tests pass
- All export formats return correct Content-Type and Content-Disposition headers
- Check endpoints return task IDs
- App starts without import errors
