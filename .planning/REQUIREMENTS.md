# Requirements: Any Auto Register

**Defined:** 2026-06-27
**Core Value:** Автоматическая регистрация аккаунтов должна работать надёжно и безопасно

## v1.5 Requirements

### Split Monoliths

- [ ] **SPLIT-01**: base_sms.py (1304 lines) → base.py, sms_activate.py, herosms.py, smsbower.py, cache.py, controller.py, factory.py
- [ ] **SPLIT-02**: chatgpt/browser_register.py (3908 lines) → selectors.py, state_machine.py, otp_flow.py, phone_challenge.py, consent_flow.py, about_you_flow.py, proxy_config.py, main class
- [ ] **SPLIT-03**: db.py (771 lines) → models.py, encryption.py, migrations.py, engine.py
- [ ] **SPLIT-04**: application/tasks.py (954 lines) → task_runner.py, task_scheduler.py, task_repository.py
- [ ] **SPLIT-05**: core/account_graph.py (1056 lines) → credentials.py, graph_ops.py, migration.py, overview.py

### Extract Patterns

- [ ] **PATT-01**: ManagedSession mixin для HTTP session lifecycle (8+ файлов)
- [ ] **PATT-02**: BasePollingMailbox с template methods для polling (13 провайдеров)
- [ ] **PATT-03**: Retry/backoff utility (5+ файлов)
- [ ] **PATT-04**: make_provider_resource() factory (13+ провайдеров)

### Merge Duplicates

- [ ] **MERG-01**: Consolidate core/mailbox/ vs providers/mailbox/ — единый canonical location
- [ ] **MERG-02**: Убрать дублирующие провайдеры из core/mailbox/ если есть в providers/mailbox/

### Type Safety

- [ ] **TYPE-01**: Type hints для BasePlatform методов (15+ методов)
- [ ] **TYPE-02**: Replace Any в RegistrationContext на конкретные типы
- [ ] **TYPE-03**: Replace Any в IdentityMaterial на MailboxAccount | None
- [ ] **TYPE-04**: Add from_config к BaseMailbox ABC

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
