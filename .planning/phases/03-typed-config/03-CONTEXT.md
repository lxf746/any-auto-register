# Phase 3: Typed Config - Context

**Gathered:** 2026-06-26
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase)

<domain>
## Phase Boundary

Заменить строковый `extra: dict` на dataclass-based конфигурацию для mailbox провайдеров. Базовый MailboxConfig dataclass + per-provider dataclass'ы с валидацией и значениями по умолчанию.

</domain>

<decisions>
## Implementation Decisions

### OpenCode's Discretion
All implementation choices are at OpenCode's discretion — pure infrastructure phase.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `core/mailbox/models.py` — MailboxAccount dataclass
- Каждый провайдер уже принимает параметры через __init__ с дефолтами
- `from_config()` classmethod извлекает ключи из dict

### Established Patterns
- Dataclass-based модели уже используются (MailboxAccount)
- Значения по умолчанию в __init__ параметрах

### Integration Points
- `create_mailbox()` передаёт resolved_extra dict в from_config()
- Провайдеры читают ключи из config dict

</code_context>

<specifics>
## Specific Ideas

No specific requirements — infrastructure phase.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>
