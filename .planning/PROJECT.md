# Any Auto Register

## What This Is

Мультиплатформенный инструмент для автоматической регистрации аккаунтов на 14+ сервисах (ChatGPT, Cursor, Windsurf, Trae, Kiro, Grok и др.). Python/FastAPI бэкенд. Использует browser automation (Playwright, Patchright, Camoufox) с anti-detection для обхода защит.

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
- ✓ Customer Portal с JWT авторизацией — existing
- ✓ Security hardening — v1.0
- ✓ Tech debt & code quality — v1.1

### Active

- [ ] Удалить Electron десктоп и React UI

### Out of Scope

- Рефакторинг монолитных файлов — отдельный milestone
- Добавление тестов — отдельный milestone
- Масштабирование (PostgreSQL, connection pooling) — отдельный milestone
- Memory leaks и thread safety — отдельный milestone
- Новые платформы — отдельный milestone

## Context

Brownfield проект. Выполнены v1.0 (Security) и v1.1 (Tech Debt). Десктопное приложение на Electron дублирует веб — API + Customer Portal покрывают все потребности.

## Constraints

- **Tech Stack**: Python 3.12, FastAPI, SQLite, SQLAlchemy
- **Совместимость**: API не должен меняться
- **Customer Portal**: Остаётся как отдельное приложение

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Удалить Electron + React | Дублирует веб, API покрывает всё | ✓ Good |
| Оставить core/desktop_apps.py | Детекция локальных IDE — core feature | ✓ Good |
| Оставить Customer Portal | Отдельное приложение, не связано с Electron | ✓ Good |

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
*Last updated: 2026-06-26 after v1.2 milestone start*
