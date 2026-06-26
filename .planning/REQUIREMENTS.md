# Requirements: Any Auto Register

**Defined:** 2026-06-26
**Core Value:** Автоматическая регистрация аккаунтов должна работать надёжно и безопасно

## v1.3 Requirements

### Module Structure

- [ ] **MODL-01**: Каждый провайдер почты — отдельный файл в `core/mailbox/`
- [ ] **MODL-02**: BaseMailbox и FallbackMailbox в `core/mailbox/base.py`
- [ ] **MODL-03**: MailboxAccount dataclass в `core/mailbox/models.py`
- [ ] **MODL-04**: `__init__.py` экспортирует публичный API

### Registry

- [ ] **REGY-01**: Единый `ProviderRegistry` класс вместо двух параллельных систем
- [ ] **REGY-02**: Декоратор `@register_provider("mailbox", "name")` для регистрации
- [ ] **REGY-03**: `create_provider()` фабрика с classmethod `from_config()`
- [ ] **REGY-04**: Автоматическое обнаружение провайдеров в `core/mailbox/`

### Configuration

- [ ] **CONF-01**: Базовый `MailboxConfig` dataclass с общими полями
- [ ] **CONF-02**: Per-provider dataclass'ы (TempMailConfig, MailTmConfig и т.д.)
- [ ] **CONF-03**: Валидация конфигурации при создании провайдера
- [ ] **CONF-04**: Значения по умолчанию для всех полей

### Resilience

- [ ] **REIL-01**: Pre-flight health check перед первым использованием провайдера
- [ ] **REIL-02**: Circuit breaker с тремя состояниями (closed/open/half-open)
- [ ] **REIL-03**: Health check caching (TTL-based)
- [ ] **REIL-04**: Email deduplication cache — не создавать дубли для одного email
- [ ] **REIL-05**: Per-provider rate limiting (configurable limits)

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Scaling

- **SCAL-01**: PostgreSQL support для mailbox state
- **SCAL-02**: Connection pooling для HTTP-провайдеров

### Testing

- **TEST-01**: Unit tests для каждого провайдера
- **TEST-02**: Integration tests для FallbackMailbox
- **TEST-03**: Mock-based tests для resilience layer

## Out of Scope

| Feature | Reason |
|---------|--------|
| Рефакторинг других монолитных файлов | Отдельный milestone |
| Добавление тестов | Отдельный milestone |
| Масштабирование (PostgreSQL) | Отдельный milestone |
| Memory leaks и thread safety | Отдельный milestone |
| Новые платформы | Отдельный milestone |
| Backward compatibility | Clean break по решению пользователя |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| MODL-01 | Phase 1 | Pending |
| MODL-02 | Phase 1 | Pending |
| MODL-03 | Phase 1 | Pending |
| MODL-04 | Phase 1 | Pending |
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
*Requirements defined: 2026-06-26*
*Last updated: 2026-06-26 after initial definition*
