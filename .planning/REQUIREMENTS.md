# Requirements: Tech Debt & Code Quality

**Defined:** 2026-06-26
**Core Value:** Кодовая база должна быть поддерживаемой, читаемой и без deprecated кода

## v1 Requirements

### Deprecated Code Cleanup

- [ ] **DEPR-01**: Удалить deprecated модуль `core/provider_drivers.py`
- [ ] **DEPR-02**: Проверить что никакой код не импортирует удалённый модуль

### DRY — Консолидация Helpers

- [ ] **DRY-01**: Консолидировать `_utcnow()` из 4 файлов в `core/datetime_utils.py`
- [ ] **DRY-02**: Консолидировать `_utcnow_iso()` и `_utcnow_ts()` в `core/datetime_utils.py`
- [ ] **DRY-03**: Обновить все импорты в затронутых файлах

### Legacy Migration Safety

- [ ] **MIGR-01**: Добавить таблицу `schema_version` для трекинга миграций
- [ ] **MIGR-02**: Legacy миграции запускаются только один раз (не при каждом старте)
- [ ] **MIGR-03**: `_migrate_legacy_accounts_schema` проверяет version перед запуском
- [ ] **MIGR-04**: `_migrate_legacy_provider_keys` проверяет version перед запуском

### Logging

- [ ] **LOG-01**: Заменить все `print()` в `core/db.py` на `logger.info()`/`logger.debug()`
- [ ] **LOG-02**: Заменить все `print()` в `core/scheduler.py` на `logger`
- [ ] **LOG-03**: Заменить все `print()` в `core/base_mailbox.py` на `logger`
- [ ] **LOG-04**: Заменить все `print()` в `services/task_runtime.py` на `logger`
- [ ] **LOG-05**: Заменить все `print()` в `services/solver_manager.py` на `logger`

### Error Handling

- [ ] **ERR-01**: Заменить bare `except:` на `except Exception:` в `services/turnstile_solver/api_solver.py`
- [ ] **ERR-02**: Добавить `logger.debug()`/`logger.warning()` в пустые `except Exception:` блоки в `services/solver_manager.py`
- [ ] **ERR-03**: Добавить логирование в пустые `except Exception:` блоки в `platforms/windsurf/browser_register.py`
- [ ] **ERR-04**: Добавить логирование в пустые `except Exception:` блоки в `platforms/trae/browser_register.py`

### Constants

- [ ] **CONST-01**: Вынести `time.sleep(3600)` в `POLL_INTERVAL_SECONDS` в `core/scheduler.py`
- [ ] **CONST-02**: Вынести `time.sleep(30)` в `LIFECYCLE_CHECK_INTERVAL` в `core/lifecycle.py`
- [ ] **CONST-03**: Вынести `time.sleep(3)` в `SMS_RETRY_DELAY` в `core/base_sms.py`

## v2 Requirements

Deferred to future milestone.

### Refactoring

- **REF-01**: Разбить `core/account_graph.py` (1060 строк) на модули
- **REF-02**: Разбить `core/base_mailbox.py` (2059 строк) по провайдерам
- **REF-03**: Разбить `core/base_sms.py` (1265 строк) по провайдерам
- **REF-04**: Разбить `platforms/chatgpt/browser_register.py` (3908 строк) по шагам
- **REF-05**: Разбить `customer_portal_api/app/services/portal.py` (1116 строк) по сервисам

### Memory & Thread Safety

- **MEM-01**: Исправить memory leak в `_task_locks` dictionary
- **MEM-02**: Исправить thread-unsafe global state в `solver_manager.py`
- **MEM-03**: Добавить pagination в scheduler (не загружать все аккаунты)
- **MEM-04**: Ограничить thread pool в `task_runtime.py`

## Out of Scope

| Feature | Reason |
|---------|--------|
| Рефакторинг больших файлов | Высокий риск, отдельный milestone |
| Memory leaks и thread safety | Отдельный milestone |
| Тесты | Отдельный milestone |
| Масштабирование | Отдельный milestone |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DEPR-01 | Phase 1 | Pending |
| DEPR-02 | Phase 1 | Pending |
| DRY-01 | Phase 1 | Pending |
| DRY-02 | Phase 1 | Pending |
| DRY-03 | Phase 1 | Pending |
| MIGR-01 | Phase 2 | Pending |
| MIGR-02 | Phase 2 | Pending |
| MIGR-03 | Phase 2 | Pending |
| MIGR-04 | Phase 2 | Pending |
| LOG-01 | Phase 3 | Pending |
| LOG-02 | Phase 3 | Pending |
| LOG-03 | Phase 3 | Pending |
| LOG-04 | Phase 3 | Pending |
| LOG-05 | Phase 3 | Pending |
| ERR-01 | Phase 4 | Pending |
| ERR-02 | Phase 4 | Pending |
| ERR-03 | Phase 4 | Pending |
| ERR-04 | Phase 4 | Pending |
| CONST-01 | Phase 5 | Pending |
| CONST-02 | Phase 5 | Pending |
| CONST-03 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 21 total
- Mapped to phases: 21
- Unmapped: 0 ✓

---
*Requirements defined: 2026-06-26*
*Last updated: 2026-06-26 after initial definition*
