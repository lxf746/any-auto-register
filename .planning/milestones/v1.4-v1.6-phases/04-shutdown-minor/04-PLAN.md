# Phase 4: Shutdown & Minor - Plan

**Created:** 2026-06-26
**Status:** Ready for execution

## Tasks

### T4.1: SHTD-01 — Scheduler.stop() join thread
- File: core/scheduler.py
- Problem: stop() doesn't join thread, 3600s sleep blocks exit
- Fix: Replace time.sleep with Event.wait(), join thread in stop()

### T4.2: SHTD-02 — LifecycleManager.stop() join thread
- File: core/lifecycle.py
- Problem: stop() doesn't join thread
- Fix: Add join() with timeout in stop()

### T4.3: SHTD-03 — TaskRuntime.stop() join workers
- File: services/task_runtime.py
- Problem: stop() doesn't join dispatcher or workers
- Fix: Join dispatcher and worker threads in stop()

### T4.4: MINR-01 — Lock ordering documentation
- File: core/base_sms.py
- Problem: Manual acquire/release is exception-fragile
- Fix: Add comments documenting lock ordering, convert to try/finally

### T4.5: MINR-02 — Subprocess pipe cleanup
- File: services/solver_manager.py
- Problem: stderr pipe leaked on early exit and stop()
- Fix: Add stderr.close() in early exit path and stop()

## Success Criteria

1. Scheduler.stop() прерывает sleep и ждёт завершения потока ✓
2. LifecycleManager.stop() ждёт завершения потока ✓
3. TaskRuntime.stop() ждёт завершения всех воркеров ✓
4. Lock ordering в base_sms.py документирован и безопасен ✓
5. Subprocess pipes закрываются во всех путях ✓

## Dependencies

Phase 1 (HTTP Sessions) — Complete
Phase 2 (Browser Resources) — Complete
Phase 3 (Memory & Thread Safety) — Complete

## Risk

Low — isolated changes, each with clear scope.
