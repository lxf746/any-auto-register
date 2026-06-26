# Phase 1: Module Split - Plan

**Created:** 2026-06-26
**Status:** Ready for execution

## Tasks

### T1.1: Create core/mailbox/ package structure
- Create `core/mailbox/__init__.py` with public API exports
- Create `core/mailbox/models.py` with MailboxAccount dataclass
- Create `core/mailbox/base.py` with BaseMailbox and FallbackMailbox

### T1.2: Extract provider modules
- Create `core/mailbox/laoudo.py` — LaoudoMailbox
- Create `core/mailbox/aitre.py` — AitreMailbox
- Create `core/mailbox/tempmail_lol.py` — TempMailLolMailbox
- Create `core/mailbox/tempmail_web.py` — TempMailWebMailbox
- Create `core/mailbox/duckmail.py` — DuckMailMailbox
- Create `core/mailbox/cfworker.py` — CFWorkerMailbox
- Create `core/mailbox/moemail.py` — MoeMailMailbox
- Create `core/mailbox/freemail.py` — FreemailMailbox
- Create `core/mailbox/testmail.py` — TestmailMailbox
- Create `core/mailbox/ddg_email.py` — DDGEmailMailbox

### T1.3: Extract factory functions and registry
- Create `core/mailbox/registry.py` with MAILBOX_FACTORY_REGISTRY and create_mailbox()
- Move all `_create_*` factory functions to registry.py
- Move default API URL constants to respective provider modules

### T1.4: Update imports
- Update `core/base_mailbox.py` to re-export from new modules (backward compat during transition)
- Update `providers/mailbox/*.py` to import from new locations
- Update `application/tasks.py` and other callers

### T1.5: Verify and cleanup
- Run `python -c "from core.mailbox import *"` to verify imports
- Remove old `core/base_mailbox.py` after all imports updated
- Run any existing tests

## Success Criteria

1. Каждый провайдер почты в отдельном файле core/mailbox/<provider>.py ✓
2. BaseMailbox и FallbackMailbox в core/mailbox/base.py ✓
3. MailboxAccount dataclass в core/mailbox/models.py ✓
4. core/mailbox/__init__.py экспортирует публичный API ✓

## Dependencies

None — this is the first phase.

## Risk

Low — pure restructuring, no behavior changes.
