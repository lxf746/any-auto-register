---
phase: 07-cleanup
plan: 01
subsystem: core
tags: [base64, mailbox, imports, deprecated, shim]

# Dependency graph
requires:
  - phase: 06-logs-debug
    provides: completed core module consolidation
provides:
  - Zero deprecated core.base_mailbox imports across 17 files
  - Deleted backward-compat shim (core/base_mailbox.py)
  - Clean v1 transition comments removed
affects: [07-02]

# Tech tracking
tech-stack:
  added: []
  patterns: [direct-submodule-imports]

key-files:
  created: [tests/test_no_deprecated_imports.py]
  modified:
    - platforms/fireworks/plugin.py
    - platforms/kimchi/plugin.py
    - platforms/cerebras/plugin.py
    - platforms/trae/plugin.py
    - platforms/windsurf/plugin.py
    - platforms/kiro/plugin.py
    - platforms/grok/plugin.py
    - platforms/openblocklabs/plugin.py
    - platforms/cursor/plugin.py
    - platforms/tavily/plugin.py
    - platforms/blackbox/plugin.py
    - platforms/blink/plugin.py
    - platforms/chatgpt/plugin.py
    - platforms/anything/plugin.py
    - core/generic_http_mailbox.py
    - core/local_ms_mailbox.py
    - application/tasks/task_runner.py
    - main.py
    - api/v2/router.py
    - api/v2/auth.py
  deleted: [core/base_mailbox.py]

key-decisions:
  - "All imports go directly to core.mailbox submodules — no shim layer"
  - "Kept _extract_verification_link alias in core files to avoid internal refactoring"

patterns-established:
  - "Direct submodule import: use core.mailbox.base, core.mailbox.models, core.mailbox.registry"

requirements-completed: [CL-01, CL-02, CL-04]

coverage:
  - id: D1
    description: "All deprecated core.base_mailbox imports replaced with direct core.mailbox submodule imports"
    requirement: CL-04
    verification:
      - kind: unit
        ref: tests/test_no_deprecated_imports.py#test_no_base_mailbox_imports
        status: pass
    human_judgment: false
  - id: D2
    description: "base_mailbox.py shim deleted, v1 transition comments cleaned"
    requirement: CL-04
    verification:
      - kind: unit
        ref: tests/test_no_deprecated_imports.py#test_no_base_mailbox_imports
        status: pass
    human_judgment: false

duration: 3min
completed: 2026-06-27
status: complete
---

# Phase 7 Plan 01: Replace deprecated imports Summary

**Replaced all 18 deprecated core.base_mailbox imports with direct core.mailbox submodule paths and deleted the backward-compat shim**

## Performance

- **Duration:** 3 min
- **Started:** 2026-06-27T12:13:48Z
- **Completed:** 2026-06-27T12:16:48Z
- **Tasks:** 2
- **Files modified:** 20 (17 imports + 4 comments + 1 deleted)

## Accomplishments
- 14 platform plugins + 2 core files + 1 task runner migrated to direct imports
- Deleted core/base_mailbox.py shim (36 lines of backward-compat re-exports)
- Cleaned 3 v1 transition comments across main.py, api/v2/router.py, api/v2/auth.py
- Added regression test to prevent future deprecated imports

## Task Commits

Each task was committed atomically:

1. **Task 1: Replace deprecated imports** - `b2f58c1` (feat, test)
2. **Task 2: Delete shim and clean comments** - `e3666c5` (feat)

**Plan metadata:** pending (docs: complete plan)

## Files Created/Modified
- `tests/test_no_deprecated_imports.py` - Regression test checking no file imports from core.base_mailbox
- `core/base_mailbox.py` - Deleted (backward-compat shim)
- `platforms/*/plugin.py` (14 files) - BaseMailbox import now from core.mailbox.base
- `core/generic_http_mailbox.py` - Split import into 3 direct submodule imports
- `core/local_ms_mailbox.py` - Split import into 3 direct submodule imports
- `application/tasks/task_runner.py` - create_mailbox import from core.mailbox.registry
- `main.py` - Removed stale v1 SPA comment
- `api/v2/router.py` - Removed "(reuse v1 logic)" from rate limiting comment
- `api/v2/auth.py` - Removed migration history from docstring

## Decisions Made
- All imports go directly to core.mailbox submodules — no shim layer
- Kept `_extract_verification_link` alias in core files to avoid internal refactoring

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed indentation on task_runner.py second import**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** Edit tool replaced first occurrence but second occurrence at line 381 got wrong indentation (4 spaces instead of 8)
- **Fix:** Manual indentation correction
- **Files modified:** application/tasks/task_runner.py
- **Verification:** grep confirms both occurrences correct
- **Committed in:** b2f58c1 (part of Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minor indentation fix. No scope creep.

## Issues Encountered
- Pre-existing test failures in test_chatgpt_oauth_requirements.py, test_tasks_herosms.py, test_validity_recovery.py (unrelated to this plan's changes)

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All deprecated imports eliminated — codebase is clean for Plan 07-02 infrastructure audit

---
*Phase: 07-cleanup*
*Completed: 2026-06-27*
