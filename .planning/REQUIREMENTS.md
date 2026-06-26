# Requirements: Any Auto Register

**Defined:** 2026-06-26
**Core Value:** Автоматическая регистрация аккаунтов должна работать надёжно и безопасно

## v1.4 Requirements

### HTTP Session Management

- [ ] **HTTP-01**: ProtocolExecutor — context manager или explicit close() в base_platform.py
- [ ] **HTTP-02**: cffi_requests.Session в lifecycle.py — один на все итерации
- [ ] **HTTP-03**: FreemailMailbox — context manager support
- [ ] **HTTP-04**: GenericHttpMailbox — context manager support
- [ ] **HTTP-05**: HTTPClient — гарантированное закрытие session
- [ ] **HTTP-06**: Any2ApiClient — persistent session
- [ ] **HTTP-07**: SMS providers — persistent sessions

### Browser Resource Management

- [ ] **BRWS-01**: TempMailWebMailbox — context manager вместо __del__
- [ ] **BRWS-02**: PlaywrightExecutor — гарантированное закрытие
- [ ] **BRWS-03**: Browser context в turnstile_solver — корректное закрытие при ошибках

### Memory Management

- [ ] **MEMO-01**: _task_locks — periodic cleanup stale entries
- [ ] **MEMO-02**: Global state — единый lock hierarchy

### Thread Safety

- [ ] **THRD-01**: _FERNET lazy init — lock
- [ ] **THRD-02**: providers/registry.py load_all() — lock
- [ ] **THRD-03**: core/registry.py _registry — lock
- [ ] **THRD-04**: solver_manager globals — lock в get_status()

### Graceful Shutdown

- [ ] **SHTD-01**: Scheduler.stop() — join thread
- [ ] **SHTD-02**: LifecycleManager.stop() — join thread
- [ ] **SHTD-03**: TaskRuntime.stop() — join workers

### Minor Issues

- [ ] **MINR-01**: Lock ordering в base_sms.py — документирован и стабилен
- [ ] **MINR-02**: Subprocess pipe в solver_manager — finally block

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
| Рефакторинг монолитных файлов | Отдельный milestone |
| Добавление тестов | Отдельный milestone |
| Масштабирование (PostgreSQL) | Отдельный milestone |
| Новые платформы | Отдельный milestone |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| HTTP-01 | Phase 1 | Pending |
| HTTP-02 | Phase 1 | Pending |
| HTTP-03 | Phase 1 | Pending |
| HTTP-04 | Phase 1 | Pending |
| HTTP-05 | Phase 1 | Pending |
| HTTP-06 | Phase 1 | Pending |
| HTTP-07 | Phase 1 | Pending |
| BRWS-01 | Phase 2 | Pending |
| BRWS-02 | Phase 2 | Pending |
| BRWS-03 | Phase 2 | Pending |
| MEMO-01 | Phase 3 | Pending |
| MEMO-02 | Phase 3 | Pending |
| THRD-01 | Phase 3 | Pending |
| THRD-02 | Phase 3 | Pending |
| THRD-03 | Phase 3 | Pending |
| THRD-04 | Phase 3 | Pending |
| SHTD-01 | Phase 4 | Pending |
| SHTD-02 | Phase 4 | Pending |
| SHTD-03 | Phase 4 | Pending |
| MINR-01 | Phase 4 | Pending |
| MINR-02 | Phase 4 | Pending |

**Coverage:**
- v1.4 requirements: 21 total
- Mapped to phases: 21
- Unmapped: 0 ✓

---
*Requirements defined: 2026-06-26*
*Last updated: 2026-06-26 after initial definition*
