# Phase 4: Resilience Layer - Context

**Gathered:** 2026-06-26
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase)

<domain>
## Phase Boundary

Добавить enterprise-возможности для mailbox провайдеров: pre-flight health checks, circuit breaker per provider, health check caching, email deduplication cache, per-provider rate limiting.

</domain>

<decisions>
## Implementation Decisions

### OpenCode's Discretion
All implementation choices are at OpenCode's discretion — pure infrastructure phase.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `core/mailbox/base.py` — BaseMailbox ABC для декорирования
- `core/mailbox/registry.py` — create_mailbox() entry point
- `core/mailbox/models.py` — MailboxAccount dataclass

### Established Patterns
- Python ABC для абстракций
- Dataclass-based конфигурация
- Logging через standard library

### Integration Points
- Health check: перед get_email() в create_mailbox()
- Circuit breaker: оборачивает каждый провайдер
- Rate limit: в каждом провайдере при вызове API
- Email dedup: в FallbackMailbox.get_email()

</code_context>

<specifics>
## Specific Ideas

No specific requirements — infrastructure phase.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>
