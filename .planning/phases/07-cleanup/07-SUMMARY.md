---
phase: 07
plan: combined
subsystem: cleanup
tags: [deprecated-imports, shim-deletion, gitignore, dockerfile, v1-cleanup]

# Dependency graph
requires:
  - phase: 06-logs-debug
    provides: completed core module consolidation
provides:
  - Zero deprecated core.base_mailbox imports
  - Deleted backward-compat shim layer
  - Clean infrastructure files (gitignore, Dockerfile, docker-compose)
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns: [direct-submodule-imports]

key-files:
  created: [tests/test_no_deprecated_imports.py]
  deleted: [core/base_mailbox.py]
  modified:
    - platforms/*/plugin.py (14 files)
    - core/generic_http_mailbox.py
    - core/local_ms_mailbox.py
    - application/tasks/task_runner.py
    - main.py
    - api/v2/router.py
    - api/v2/auth.py
    - .gitignore
    - Dockerfile

key-decisions:
  - "All imports go directly to core.mailbox submodules — no shim layer"
  - "Replaced retrospective v1 comment with forward-looking note"

patterns-established:
  - "Direct submodule import: use core.mailbox.base, core.mailbox.models, core.mailbox.registry"

requirements-completed: [CL-01, CL-02, CL-03, CL-04]

coverage:
  - id: D1
    description: "All deprecated core.base_mailbox imports replaced with direct submodule imports"
    requirement: CL-04
    verification:
      - kind: unit
        ref: tests/test_no_deprecated_imports.py#test_no_base_mailbox_imports
        status: pass
    human_judgment: false
  - id: D2
    description: "base_mailbox.py shim deleted and v1 transition comments cleaned"
    requirement: CL-04
    verification:
      - kind: unit
        ref: "grep: zero remaining core.base_mailbox imports"
        status: pass
    human_judgment: false
  - id: D3
    description: ".gitignore cleaned of stale v1 comments"
    requirement: CL-01
    verification:
      - kind: unit
        ref: "grep: ! grep -q 'old frontend' .gitignore"
        status: pass
    human_judgment: false
  - id: D4
    description: "Dockerfile references only frontend-new/ (not frontend/)"
    requirement: CL-02
    verification:
      - kind: unit
        ref: "grep: ! grep -q 'rm -rf.*frontend[^-]' Dockerfile"
        status: pass
    human_judgment: false
  - id: D5
    description: "docker-compose.yml confirmed clean (app + postgres only)"
    requirement: CL-03
    verification:
      - kind: unit
        ref: "manual: docker-compose.yml contains only app and postgres"
        status: pass
    human_judgment: false

duration: 4min
completed: 2026-06-27
status: complete
---

# Phase 7: Cleanup Summary

**Deleted base_mailbox shim, replaced 18 deprecated imports with direct core.mailbox submodule paths, cleaned infrastructure files**

## Performance

- **Duration:** 4 min (plan 01: 3min, plan 02: 1min)
- **Started:** 2026-06-27T12:13:48Z
- **Completed:** 2026-06-27T12:17:48Z
- **Tasks:** 4 (2 per plan)
- **Files modified:** 22

## Accomplishments
- 18 deprecated core.base_mailbox imports migrated to direct submodule paths
- Deleted core/base_mailbox.py backward-compat shim (36 lines)
- Cleaned v1 transition comments from main.py, api/v2/router.py, api/v2/auth.py
- Added regression test preventing future deprecated imports
- .gitignore cleaned of stale v1 comment
- Dockerfile rm command no longer references non-existent frontend/ directory
- docker-compose.yml confirmed clean (no legacy services)

## Task Commits

1. **07-01 Task 1: Replace deprecated imports** - `b2f58c1` (feat, test)
2. **07-01 Task 2: Delete shim and clean comments** - `e3666c5` (feat)
3. **07-02 Task 1: Clean .gitignore** - `4ae237f` (chore)
4. **07-02 Task 2: Clean Dockerfile** - `12736ac` (chore)

## Files Created/Modified
- `tests/test_no_deprecated_imports.py` - Regression test
- `core/base_mailbox.py` - Deleted (backward-compat shim)
- `platforms/*/plugin.py` (14 files) - BaseMailbox import now from core.mailbox.base
- `core/generic_http_mailbox.py` - Split import into 3 direct submodule imports
- `core/local_ms_mailbox.py` - Split import into 3 direct submodule imports
- `application/tasks/task_runner.py` - create_mailbox import from core.mailbox.registry
- `main.py` - Removed stale v1 SPA comment
- `api/v2/router.py` - Removed "(reuse v1 logic)" from rate limiting comment
- `api/v2/auth.py` - Removed migration history from docstring
- `.gitignore` - Replaced stale v1 comment
- `Dockerfile` - Removed non-existent frontend/ from rm command

## Decisions Made
- All imports go directly to core.mailbox submodules — no shim layer
- Kept `_extract_verification_link` alias in core files to avoid internal refactoring
- Replaced retrospective v1 comment with forward-looking note

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed indentation on task_runner.py second import**
- **Found during:** 07-01 Task 1 (GREEN phase)
- **Issue:** Edit tool replaced first occurrence but second at line 381 got wrong indentation
- **Fix:** Manual indentation correction
- **Committed in:** b2f58c1

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minor indentation fix. No scope creep.

## Issues Encountered
- Pre-existing test failures in test_chatgpt_oauth_requirements.py, test_tasks_herosms.py, test_validity_recovery.py (unrelated to this phase)

## User Setup Required
None

## Next Phase Readiness
- Phase 7 complete — codebase clean of deprecated imports and v1 artifacts
- Ready for Phase 8 or milestone completion

---
*Phase: 07-cleanup*
*Completed: 2026-06-27*

## Self-Check: PASSED
