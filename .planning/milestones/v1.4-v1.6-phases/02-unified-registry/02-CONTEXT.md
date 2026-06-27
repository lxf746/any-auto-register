# Phase 2: Unified Registry - Context

**Gathered:** 2026-06-26
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase)

<domain>
## Phase Boundary

Заменить две параллельные системы реестра (`MAILBOX_FACTORY_REGISTRY` в `core/mailbox/registry.py` и `_registry` в `providers/registry.py`) на единую. Единый реестр — `providers/registry.py`. Mailbox провайдеры должны использовать `from_config()` classmethod.

</domain>

<decisions>
## Implementation Decisions

### OpenCode's Discretion
All implementation choices are at OpenCode's discretion — pure infrastructure phase.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `providers/registry.py` — уже имеет register_provider(), create_provider(), load_all()
- `providers/mailbox/*.py` — уже регистрируют провайдеры через @register_provider
- `core/mailbox/registry.py` — MAILBOX_FACTORY_REGISTRY с _create_* функциями

### Established Patterns
- Декоратор @register_provider("type", "name") для регистрации
- from_config(config) classmethod для создания инстансов
- load_all() для авто-обнаружения провайдеров

### Integration Points
- create_mailbox() использует MAILBOX_FACTORY_REGISTRY для создания инстансов
- providers/mailbox/*.py регистрируют классы в _registry

</code_context>

<specifics>
## Specific Ideas

No specific requirements — infrastructure phase.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>
