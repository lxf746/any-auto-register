# Phase 1: HTTP Sessions - Plan

**Created:** 2026-06-26
**Status:** Ready for execution

## Tasks

### T1.1: Fix ProtocolExecutor usage in base_platform.py
- Read how _make_executor() is called in application/tasks.py
- Ensure all callers use context manager or explicit close()
- Add __enter__/__exit__ to _make_executor() wrapper

### T1.2: Fix lifecycle.py session leak
- Create cffi_requests.Session once before the loop
- Reuse it for all iterations
- Close it after the loop

### T1.3: Add context manager to FreemailMailbox
- Add close() method
- Add __enter__/__exit__
- Lazy session creation with proper cleanup

### T1.4: Add context manager to GenericHttpMailbox
- Add close() method
- Add __enter__/__exit__
- Lazy session creation with proper cleanup

### T1.5: Fix HTTPClient session lifecycle
- Ensure session is closed when HTTPClient is garbage collected
- Add __del__ as safety net

### T1.6: Fix Any2ApiClient to use persistent session
- Create requests.Session once in __init__
- Reuse for all _post/_put calls

### T1.7: Fix SMS providers to use persistent sessions
- SmsActivateProvider — add self._session
- HeroSmsProvider — add self._session
- SmsBowerProvider — add self._session

## Success Criteria

1. ProtocolExecutor используется через context manager ✓
2. cffi_requests.Session в lifecycle.py создаётся один раз ✓
3. FreemailMailbox и GenericHttpMailbox имеют context manager ✓
4. HTTPClient гарантированно закрывает session ✓
5. Any2ApiClient использует persistent session ✓
6. SMS providers используют persistent sessions ✓

## Dependencies

None — first phase.

## Risk

Medium — changing resource management patterns.
