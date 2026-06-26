# Phase 1: Module Split - Context

**Gathered:** 2026-06-26
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase)

<domain>
## Phase Boundary

Разбить монолитный `core/base_mailbox.py` (2059 строк, 11 классов провайдеров) на отдельные модули в `core/mailbox/`. Каждый провайдер почты — отдельный файл. BaseMailbox, FallbackMailbox, MailboxAccount — в отдельных модулях.

</domain>

<decisions>
## Implementation Decisions

### OpenCode's Discretion
All implementation choices are at OpenCode's discretion — pure infrastructure phase. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `BaseMailbox` ABC — abstract base class with get_email(), wait_for_code(), wait_for_link(), get_current_ids()
- `FallbackMailbox` — failover chain implementation
- `MailboxAccount` dataclass — email, account_id, extra dict
- 11 provider classes: LaoudoMailbox, AitreMailbox, TempMailLolMailbox, TempMailWebMailbox, DuckMailMailbox, CFWorkerMailbox, MoeMailMailbox, FreemailMailbox, TestmailMailbox, DDGEmailMailbox
- `MAILBOX_FACTORY_REGISTRY` — dict mapping driver_type to factory functions
- `create_mailbox()` — entry point with fallback chain building
- 14 `_create_*` factory functions
- Default API URLs as module-level constants

### Established Patterns
- Each provider in `providers/mailbox/*.py` is a thin wrapper that imports from `core/base_mailbox.py` and registers via `register_provider()`
- Factory pattern: `_create_*(extra, proxy) -> BaseMailbox`
- Configuration via `extra: dict` — stringly-typed, no validation

### Integration Points
- `create_mailbox()` called from `application/tasks.py::_build_platform_instance()`
- Platforms receive `mailbox: BaseMailbox` via constructor
- `providers/mailbox/*.py` files import and re-register providers
- `MAILBOX_FACTORY_REGISTRY` used by `create_mailbox()` for provider instantiation

</code_context>

<specifics>
## Specific Ideas

No specific requirements — infrastructure phase. Refer to ROADMAP phase description and success criteria.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>
