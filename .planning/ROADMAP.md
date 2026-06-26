# Roadmap: v1.3 Enterprise Email Provider Abstractions

**Milestone:** v1.3
**Phases:** 4
**Requirements:** 17

## Phase 1: Module Split

**Goal:** Разбить base_mailbox.py (2059 строк, 11 классов) на отдельные модули

**Requirements:** MODL-01, MODL-02, MODL-03, MODL-04

**Success criteria:**
1. Каждый провайдер почты в отдельном файле core/mailbox/<provider>.py
2. BaseMailbox и FallbackMailbox в core/mailbox/base.py
3. MailboxAccount dataclass в core/mailbox/models.py
4. core/mailbox/__init__.py экспортирует публичный API

## Phase 2: Unified Registry

**Goal:** Заменить две параллельные системы реестра на единую

**Requirements:** REGY-01, REGY-02, REGY-03, REGY-04

**Success criteria:**
1. ProviderRegistry класс取代ляет MAILBOX_FACTORY_REGISTRY и _registry["mailbox"]
2. Декоратор @register_provider работает для всех типов провайдеров
3. create_provider() фабрика использует from_config() classmethod
4. Автоматическое обнаружение провайдеров при импорте core/mailbox

## Phase 3: Typed Config

**Goal:** Заменить строковый extra dict на dataclass-based конфигурацию

**Requirements:** CONF-01, CONF-02, CONF-03, CONF-04

**Success criteria:**
1. Базовый MailboxConfig dataclass определён
2. Per-provider dataclass'ы для каждого провайдера
3. Валидация конфигурации при создании провайдера
4. Все поля имеют значения по умолчанию

## Phase 4: Resilience Layer

**Goal:** Добавить enterprise-возможности для провайдеров

**Requirements:** REIL-01, REIL-02, REIL-03, REIL-04, REIL-05

**Success criteria:**
1. Pre-flight health check выполняется перед первым использованием
2. Circuit breaker переключается между closed/open/half-open
3. Health check результаты кэшируются с TTL
4. Email dedup не создаёт дубли для одного адреса
5. Per-provider rate limits конфигурируются

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| MODL-01 | Phase 1 | Complete |
| MODL-02 | Phase 1 | Complete |
| MODL-03 | Phase 1 | Complete |
| MODL-04 | Phase 1 | Complete |
| REGY-01 | Phase 2 | Pending |
| REGY-02 | Phase 2 | Pending |
| REGY-03 | Phase 2 | Pending |
| REGY-04 | Phase 2 | Pending |
| CONF-01 | Phase 3 | Pending |
| CONF-02 | Phase 3 | Pending |
| CONF-03 | Phase 3 | Pending |
| CONF-04 | Phase 3 | Pending |
| REIL-01 | Phase 4 | Pending |
| REIL-02 | Phase 4 | Pending |
| REIL-03 | Phase 4 | Pending |
| REIL-04 | Phase 4 | Pending |
| REIL-05 | Phase 4 | Pending |

**Coverage:**
- v1.3 requirements: 17 total
- Mapped to phases: 17
- Unmapped: 0 ✓

---
*Roadmap created: 2026-06-26*
*Last updated: 2026-06-26 after initial creation*
