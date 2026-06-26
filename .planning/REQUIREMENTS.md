# Requirements: Any Auto Register

**Defined:** 2026-06-26
**Core Value:** Автоматическая регистрация аккаунтов должна работать надёжно и безопасно

## v1.4 Requirements

### HTTP Session Management

- [x] **HTTP-01**: ProtocolExecutor — context manager или explicit close() в base_platform.py
- [x] **HTTP-02**: cffi_requests.Session в lifecycle.py — один на все итерации
- [x] **HTTP-03**: FreemailMailbox — context manager support
- [x] **HTTP-04**: GenericHttpMailbox — context manager support
- [x] **HTTP-05**: HTTPClient — гарантированное закрытие session
- [x] **HTTP-06**: Any2ApiClient — persistent session
- [x] **HTTP-07**: SMS providers — persistent sessions

### Browser Resource Management

- [x] **BRWS-01**: TempMailWebMailbox — context manager вместо __del__
- [x] **BRWS-02**: PlaywrightExecutor — гарантированное закрытие
- [x] **BRWS-03**: Browser context в turnstile_solver — корректное закрытие при ошибках

### Memory Management

- [x] **MEMO-01**: _task_locks — periodic cleanup stale entries
- [x] **MEMO-02**: Global state — единый lock hierarchy

### Thread Safety

- [x] **THRD-01**: _FERNET lazy init — lock
- [x] **THRD-02**: providers/registry.py load_all() — lock
- [x] **THRD-03**: core/registry.py _registry — lock
- [x] **THRD-04**: solver_manager globals — lock в get_status()

### Graceful Shutdown

- [x] **SHTD-01**: Scheduler.stop() — join thread
- [x] **SHTD-02**: LifecycleManager.stop() — join thread
- [x] **SHTD-03**: TaskRuntime.stop() — join workers

### Minor Issues

- [x] **MINR-01**: Lock ordering в base_sms.py — документирован и стабилен
- [x] **MINR-02**: Subprocess pipe в solver_manager — finally block

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
| HTTP-01 | Phase 1 | Complete |
| HTTP-02 | Phase 1 | Complete |
| HTTP-03 | Phase 1 | Complete |
| HTTP-04 | Phase 1 | Complete |
| HTTP-05 | Phase 1 | Complete |
| HTTP-06 | Phase 1 | Complete |
| HTTP-07 | Phase 1 | Complete |
| BRWS-01 | Phase 2 | Complete |
| BRWS-02 | Phase 2 | Complete |
| BRWS-03 | Phase 2 | Complete |
| MEMO-01 | Phase 3 | Complete |
| MEMO-02 | Phase 3 | Complete |
| THRD-01 | Phase 3 | Complete |
| THRD-02 | Phase 3 | Complete |
| THRD-03 | Phase 3 | Complete |
| THRD-04 | Phase 3 | Complete |
| SHTD-01 | Phase 4 | Complete |
| SHTD-02 | Phase 4 | Complete |
| SHTD-03 | Phase 4 | Complete |
| MINR-01 | Phase 4 | Complete |
| MINR-02 | Phase 4 | Complete |

**Coverage:**
- v1.4 requirements: 21 total
- Mapped to phases: 21
- Unmapped: 0 ✓

---
*Requirements defined: 2026-06-26*
*Last updated: 2026-06-26 after initial definition*
