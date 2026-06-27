# Requirements: Any Auto Register

**Defined:** 2026-06-27
**Core Value:** Автоматическая регистрация аккаунтов должна работать надёжно и безопасно

## v1.5 Requirements

### Split Monoliths

- [x] **SPLIT-01**: base_sms.py (1304 lines) → 7 modules
- [x] **SPLIT-02**: chatgpt/browser_register.py (3908 lines) → 12 modules
- [x] **SPLIT-03**: db.py (771 lines) → 4 modules
- [x] **SPLIT-04**: tasks.py (954 lines) → 3 modules
- [x] **SPLIT-05**: account_graph.py (1056 lines) → 5 modules

### Extract Patterns

- [x] **PATT-01**: ManagedSession mixin
- [x] **PATT-02**: BasePollingMailbox
- [x] **PATT-03**: Retry/backoff utility
- [x] **PATT-04**: make_provider_resource() factory

### Merge Duplicates

- [x] **MERG-01**: Consolidate core/mailbox/ vs providers/mailbox/
- [x] **MERG-02**: Убрать дублирующие провайдеры

### Type Safety

- [x] **TYPE-01**: Type hints для BasePlatform
- [x] **TYPE-02**: Replace Any в RegistrationContext
- [x] **TYPE-03**: Replace Any в IdentityMaterial
- [x] **TYPE-04**: Add from_config к BaseMailbox ABC

## v2 Requirements

### Testing

- **TEST-01**: Unit tests для core модулей
- **TEST-02**: Integration tests для mailbox providers
- **TEST-03**: Stress tests для concurrent registration

### Scaling

- **SCAL-01**: PostgreSQL support
- **SCAL-02**: Connection pooling

## Out of Scope

| Feature | Reason |
|---------|--------|
| Новые платформы | Отдельный milestone |
| Масштабирование (PostgreSQL) | Отдельный milestone |
| Добавление тестов | Отдельный milestone |
| Мониторинг и метрики | Отдельный milestone |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SPLIT-01 | Phase 1 | Pending |
| SPLIT-02 | Phase 1 | Pending |
| SPLIT-03 | Phase 1 | Pending |
| SPLIT-04 | Phase 1 | Pending |
| SPLIT-05 | Phase 1 | Pending |
| PATT-01 | Phase 2 | Pending |
| PATT-02 | Phase 2 | Pending |
| PATT-03 | Phase 2 | Pending |
| PATT-04 | Phase 2 | Pending |
| MERG-01 | Phase 3 | Pending |
| MERG-02 | Phase 3 | Pending |
| TYPE-01 | Phase 4 | Pending |
| TYPE-02 | Phase 4 | Pending |
| TYPE-03 | Phase 4 | Pending |
| TYPE-04 | Phase 4 | Pending |

**Coverage:**
- v1.5 requirements: 15 total
- Mapped to phases: 15
- Unmapped: 0 ✓

---
*Requirements defined: 2026-06-27*
*Last updated: 2026-06-27 after initial definition*
