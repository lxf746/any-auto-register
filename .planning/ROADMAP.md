# Roadmap: Tech Debt & Code Quality

**Milestone:** v1.1 Tech Debt & Code Quality
**Created:** 2026-06-26

## Phase Overview

| # | Phase | Goal | Requirements | Success Criteria |
|---|-------|------|--------------|------------------|
| 4 | Deprecated Code & DRY | Удалить deprecated код и консолидировать дублированные helpers | DEPR-01, DEPR-02, DRY-01, DRY-02, DRY-03 | 5 |
| 5 | Legacy Migration Safety | Остановить повторный запуск legacy миграций | MIGR-01, MIGR-02, MIGR-03, MIGR-04 | 4 |
| 6 | Logging | Заменить print() на logging модуль | LOG-01, LOG-02, LOG-03, LOG-04, LOG-05 | 5 |
| 7 | Error Handling | Исправить bare except и молчаливое проглатывание | ERR-01, ERR-02, ERR-03, ERR-04 | 4 |
| 8 | Constants | Вынести magic numbers в именованные константы | CONST-01, CONST-02, CONST-03 | 3 |

**Total: 5 phases | 21 requirements | All covered ✓**

## Phase Details

### Phase 4: Deprecated Code & DRY

**Goal:** Удалить deprecated модуль и консолидировать дублированные datetime helpers

**Requirements:**
- DEPR-01: Удалить deprecated модуль `core/provider_drivers.py`
- DEPR-02: Проверить что никакой код не импортирует удалённый модуль
- DRY-01: Консолидировать `_utcnow()` из 4 файлов в `core/datetime_utils.py`
- DRY-02: Консолидировать `_utcnow_iso()` и `_utcnow_ts()` в `core/datetime_utils.py`
- DRY-03: Обновить все импорты в затронутых файлах

**Success criteria:**
1. `core/provider_drivers.py` удалён
2. `grep -r "provider_drivers" .` не находит импортов
3. `core/datetime_utils.py` содержит `_utcnow`, `_utcnow_iso`, `_utcnow_ts`
4. `core/db.py`, `core/lifecycle.py`, `core/account_graph.py`, `application/tasks.py` импортируют из `core/datetime_utils.py`
5. Нет дублированных определений `_utcnow` в кодовой базе

**Files to modify:**
- `core/provider_drivers.py` — удалить
- `core/datetime_utils.py` — добавить функции
- `core/db.py` — обновить импорт
- `core/lifecycle.py` — обновить импорт
- `core/account_graph.py` — обновить импорт
- `application/tasks.py` — обновить импорт

---

### Phase 5: Legacy Migration Safety

**Goal:** Остановить повторный запуск legacy миграций через version tracking

**Requirements:**
- MIGR-01: Добавить таблицу `schema_version` для трекинга миграций
- MIGR-02: Legacy миграции запускаются только один раз
- MIGR-03: `_migrate_legacy_accounts_schema` проверяет version перед запуском
- MIGR-04: `_migrate_legacy_provider_keys` проверяет version перед запуском

**Success criteria:**
1. Таблица `schema_version` создаётся при старте
2. Каждая миграция записывает свой ID в `schema_version` после выполнения
3. `_migrate_legacy_accounts_schema` пропускается если миграция уже выполнена
4. `_migrate_legacy_provider_keys` пропускается если миграция уже выполнена

**Files to modify:**
- `core/db.py` — добавить таблицу `schema_version`, изменить логику миграций

---

### Phase 6: Logging

**Goal:** Заменить все print() на logging модуль

**Requirements:**
- LOG-01: Заменить `print()` в `core/db.py`
- LOG-02: Заменить `print()` в `core/scheduler.py`
- LOG-03: Заменить `print()` в `core/base_mailbox.py`
- LOG-04: Заменить `print()` в `services/task_runtime.py`
- LOG-05: Заменить `print()` в `services/solver_manager.py`

**Success criteria:**
1. Все `print()` в перечисленных файлах заменены на `logger.info()`/`logger.debug()`/`logger.error()`
2. Каждый модуль имеет `logger = logging.getLogger(__name__)`
3. `grep -rn "print(" core/db.py core/scheduler.py core/base_mailbox.py services/task_runtime.py services/solver_manager.py` не находит результатов

**Files to modify:**
- `core/db.py`
- `core/scheduler.py`
- `core/base_mailbox.py`
- `services/task_runtime.py`
- `services/solver_manager.py`

---

### Phase 7: Error Handling

**Goal:** Исправить bare except и добавить логирование в проглоченные ошибки

**Requirements:**
- ERR-01: Заменить bare `except:` на `except Exception:` в `services/turnstile_solver/api_solver.py`
- ERR-02: Добавить логирование в пустые `except Exception:` в `services/solver_manager.py`
- ERR-03: Добавить логирование в пустые `except Exception:` в `platforms/windsurf/browser_register.py`
- ERR-04: Добавить логирование в пустые `except Exception:` в `platforms/trae/browser_register.py`

**Success criteria:**
1. Нет bare `except:` (без типа) в `api_solver.py`
2. Пустые `except Exception:` блоки в `solver_manager.py` содержат `logger.debug()`
3. Пустые `except Exception:` блоки в `windsurf/browser_register.py` содержат `logger.debug()`
4. Пустые `except Exception:` блоки в `trae/browser_register.py` содержат `logger.debug()`

**Files to modify:**
- `services/turnstile_solver/api_solver.py`
- `services/solver_manager.py`
- `platforms/windsurf/browser_register.py`
- `platforms/trae/browser_register.py`

---

### Phase 8: Constants

**Goal:** Вынести magic numbers в именованные константы

**Requirements:**
- CONST-01: Вынести `time.sleep(3600)` в `POLL_INTERVAL_SECONDS` в `core/scheduler.py`
- CONST-02: Вынести `time.sleep(30)` в `LIFECYCLE_CHECK_INTERVAL` в `core/lifecycle.py`
- CONST-03: Вынести `time.sleep(3)` в `SMS_RETRY_DELAY` в `core/base_sms.py`

**Success criteria:**
1. `core/scheduler.py` использует `POLL_INTERVAL_SECONDS = 3600`
2. `core/lifecycle.py` использует `LIFECYCLE_CHECK_INTERVAL = 30`
3. `core/base_sms.py` использует `SMS_RETRY_DELAY = 3`
4. Нет magic numbers `3600`, `30`, `3` в `time.sleep()` вызовах в этих файлах

**Files to modify:**
- `core/scheduler.py`
- `core/lifecycle.py`
- `core/base_sms.py`

---
*Created: 2026-06-26*
