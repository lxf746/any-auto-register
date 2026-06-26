# Phase 2: Browser Resources - Plan

**Created:** 2026-06-26
**Status:** Ready for execution

## Tasks

### T2.1: Fix TempMailWebMailbox cleanup
- Add close() method
- Add __enter__/__exit__ for context manager
- Replace __del__ with proper cleanup

### T2.2: Verify PlaywrightExecutor context manager usage
- Check all callers use context manager
- Already has close() and __enter__/__exit__

### T2.3: Fix turnstile_solver browser context leak
- Initialize context = None before try block
- Ensure context.close() is only called if context was created

## Success Criteria

1. TempMailWebMailbox использует context manager вместо __del__ ✓
2. PlaywrightExecutor гарантированно закрывается ✓
3. Browser context в turnstile_solver корректно закрывается при ошибках ✓

## Dependencies

Phase 1 (HTTP Sessions) — Complete

## Risk

Medium — browser resource management is tricky.
