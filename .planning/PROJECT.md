# Any Auto Register

## What This Is

Мультиплатформенный инструмент для автоматической регистрации аккаунтов на 14+ сервисах (ChatGPT, Cursor, Windsurf, Trae, Kiro, Grok и др.). Python/FastAPI бэкенд, React фронтенд, Electron десктоп. Использует browser automation (Playwright, Patchright, Camoufox) с anti-detection для обхода защит.

## Core Value

Автоматическая регистрация аккаунтов должна работать надёжно и безопасно — аккаунты создаются, данные защищены, система не подвержена компрометации.

## Requirements

### Validated

- ✓ Регистрация аккаунтов на 14+ платформах — existing
- ✓ SMS-верификация через провайдеров — existing
- ✓ Email-верификация через временные ящики — existing
- ✓ Решение капчи (YesCaptcha, 2Captcha) — existing
- ✓ Browser automation с anti-detection — existing
- ✓ REST API для управления — existing
- ✓ React фронтенд — existing
- ✓ Electron десктоп — existing
- ✓ Customer Portal с JWT авторизацией — existing
- ✓ Security hardening (timing-safe, session tokens, encryption, CORS, TLS) — v1.0

### Active

- [ ] Удалить deprecated модули
- [ ] Консолидировать дублированные helper-функции
- [ ] Добавить version tracking для legacy миграций
- [ ] Заменить print() на logging модуль
- [ ] Исправить bare except и молчаливое проглатывание ошибок
- [ ] Вынести magic numbers в именованные константы

### Out of Scope

- Рефакторинг монолитных файлов — отдельный milestone
- Memory leaks и thread safety — отдельный milestone
- Добавление тестов — отдельный milestone
- Масштабирование (PostgreSQL, connection pooling) — отдельный milestone
- Новые платформы — отдельный milestone

## Context

Brownfield проект с существующей кодовой базой. Кодовая карта в `.planning/codebase/`. после v1.0 Security Hardening исправлены критические проблемы безопасности.

**Оставшиеся проблемы (CONCERNS.md):**
- Deprecated модуль `core/provider_drivers.py` всё ещё существует
- `_utcnow()` дублируется в 4 файлах
- Legacy миграции запускаются при каждом старте
- 643+ `except Exception` с молчаливым проглатыванием
- `print()` вместо `logging` в 20+ местах
- Magic numbers без констант

## Constraints

- **Tech Stack**: Python 3.12, FastAPI, SQLite, SQLAlchemy
- **Совместимость**: Изменения не должны ломать существующий API
- **Обратная совместимость**: Поведение не должно меняться для пользователей

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Не трогать рефакторинг больших файлов | Отдельный milestone, высокий риск | ✓ Good |
| Не трогать тесты | Отдельный milestone | ✓ Good |
| Консолидация datetime helpers в core/datetime_utils.py | DRY, уже существует файл | ✓ Good |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-26 after v1.1 milestone start*
