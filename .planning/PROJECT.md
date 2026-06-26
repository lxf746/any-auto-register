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

### Active

- [ ] Исправить критические проблемы безопасности
- [ ] Исправить высокие проблемы безопасности

### Out of Scope

- Рефакторинг монолитных файлов — отдельный milestone
- Добавление тестов — отдельный milestone
- Масштабирование (PostgreSQL, connection pooling) — отдельный milestone
- Новые платформы — отдельный milestone

## Context

Brownfield проект с существующей кодовой базой. Кодовая карта в `.planning/codebase/`. Основные проблемы безопасности выявлены в `.planning/codebase/CONCERNS.md`.

**Критические находки по безопасности:**
- Пароли сравниваются через `==` (timing attack)
- Пароль используется как JWT-токен
- Дефолтный JWT секрет `"change-me-in-production"`
- Дефолтные креды админа `admin/admin123456`
- CORS允许所有来源
- Пароли хранятся в открытом виде в SQLite
- TLS-верификация отключена по умолчанию

## Constraints

- **Tech Stack**: Python 3.12, FastAPI, SQLite, SQLAlchemy
- **Совместимость**: Изменения не должны ломать существующий API
- **Безопасность**: Все критические проблемы должны быть исправлены до продакшена

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Фокус только на безопасности | Приоритет критических проблем | — Pending |
| Не трогать существующий API contract | Обратная совместимость | — Pending |

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
*Last updated: 2026-06-26 after initialization*
