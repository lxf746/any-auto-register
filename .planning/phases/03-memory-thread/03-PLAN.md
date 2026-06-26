# Phase 3: Memory & Thread Safety - Plan

**Created:** 2026-06-26
**Status:** Ready for execution

## Tasks

### T3.1: MEMO-01 — Cleanup stale _task_locks
- File: application/tasks.py
- Problem: _task_locks dict never cleaned up, grows unbounded
- Fix: Remove lock from _task_locks when task reaches terminal status

### T3.2: THRD-01 — _FERNET lazy init lock
- File: core/db.py
- Problem: No lock on lazy init, redundant PBKDF2 computation
- Fix: Add threading.Lock around _get_fernet()

### T3.3: THRD-02 — providers/registry.py load_all() lock
- File: providers/registry.py
- Problem: No lock on load_all(), concurrent imports
- Fix: Add threading.Lock + _loaded guard

### T3.4: THRD-03 — core/registry.py _registry lock
- File: core/registry.py
- Problem: No lock on _registry, concurrent mutation/iteration
- Fix: Add threading.Lock + _loaded guard for load_all()

### T3.5: THRD-04 — solver_manager get_status() lock
- File: services/solver_manager.py
- Problem: get_status() reads globals without _lock
- Fix: Wrap get_status() body with _lock

### T3.6: MEMO-02 — Lock ordering documentation
- Add comments documenting lock acquisition order to prevent deadlocks

## Success Criteria

1. _task_locks очищается при завершении задач ✓
2. _FERNET lazy init защищён lock ✓
3. providers/registry.py load_all() защищён lock ✓
4. core/registry.py _registry защищён lock ✓
5. solver_manager.get_status() защищён lock ✓

## Dependencies

Phase 1 (HTTP Sessions) — Complete
Phase 2 (Browser Resources) — Complete

## Risk

Medium — concurrent code changes, but each is isolated.
