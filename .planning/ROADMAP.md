# Roadmap: v1.4 Memory Leaks & Thread Safety

**Milestone:** v1.4
**Phases:** 4
**Requirements:** 21

## Phase 1: HTTP Sessions

**Goal:** Исправить все HTTP session leaks — ProtocolExecutor, lifecycle.py, mailbox sessions, SMS providers

**Requirements:** HTTP-01, HTTP-02, HTTP-03, HTTP-04, HTTP-05, HTTP-06, HTTP-07

**Success criteria:**
1. ProtocolExecutor используется через context manager
2. cffi_requests.Session в lifecycle.py создаётся один раз
3. FreemailMailbox и GenericHttpMailbox имеют context manager
4. HTTPClient гарантированно закрывает session
5. Any2ApiClient использует persistent session
6. SMS providers используют persistent sessions

## Phase 2: Browser Resources

**Goal:** Исправить browser и executor leaks

**Requirements:** BRWS-01, BRWS-02, BRWS-03

**Success criteria:**
1. TempMailWebMailbox использует context manager вместо __del__
2. PlaywrightExecutor гарантированно закрывается
3. Browser context в turnstile_solver корректно закрывается при ошибках

## Phase 3: Memory & Thread

**Goal:** Исправить memory leaks и thread safety

**Requirements:** MEMO-01, MEMO-02, THRD-01, THRD-02, THRD-03, THRD-04

**Success criteria:**
1. _task_locks очищается периодически
2. Global state защищено единым lock hierarchy
3. _FERNET lazy init защищён lock
4. providers/registry.py load_all() защищён lock
5. core/registry.py _registry защищён lock
6. solver_manager globals защищены lock

## Phase 4: Shutdown & Minor

**Goal:** Graceful shutdown + minor fixes

**Requirements:** SHTD-01, SHTD-02, SHTD-03, MINR-01, MINR-02

**Success criteria:**
1. Scheduler.stop() join'ит background thread
2. LifecycleManager.stop() join'ит background thread
3. TaskRuntime.stop() join'ит worker threads
4. Lock ordering в base_sms.py документирован
5. Subprocess pipe в solver_manager закрывается в finally

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| HTTP-01 | Phase 1 | Complete |
| HTTP-02 | Phase 1 | Complete |
| HTTP-03 | Phase 1 | Complete |
| HTTP-04 | Phase 1 | Complete |
| HTTP-05 | Phase 1 | Complete |
| HTTP-06 | Phase 1 | Complete |
| HTTP-07 | Phase 1 | Complete |
| BRWS-01 | Phase 2 | Complete |
| BRWS-02 | Phase 2 | Complete |
| BRWS-03 | Phase 2 | Complete |
| MEMO-01 | Phase 3 | Pending |
| MEMO-02 | Phase 3 | Pending |
| THRD-01 | Phase 3 | Pending |
| THRD-02 | Phase 3 | Pending |
| THRD-03 | Phase 3 | Pending |
| THRD-04 | Phase 3 | Pending |
| SHTD-01 | Phase 4 | Pending |
| SHTD-02 | Phase 4 | Pending |
| SHTD-03 | Phase 4 | Pending |
| MINR-01 | Phase 4 | Pending |
| MINR-02 | Phase 4 | Pending |

**Coverage:**
- v1.4 requirements: 21 total
- Mapped to phases: 21
- Unmapped: 0 ✓

---
*Roadmap created: 2026-06-26*
*Last updated: 2026-06-26 after initial creation*
