# Any Auto Register

## What This Is

Мультиплатформенный инструмент для автоматической регистрации аккаунтов на 14+ сервисах (ChatGPT, Cursor, Windsurf, Trae, Kiro, Grok и др.). Python/FastAPI бэкенд. Использует browser automation (Playwright, Patchright, Camoufox) с anti-detection для обхода защит.

## Core Value

Автоматическая регистрация аккаунтов должна работать надёжно и безопасно — аккаунты создаются, данные защищены, система не подвержена компрометации.

## Current Milestone: v1.4 Memory Leaks & Thread Safety

**Goal:** Исправить все утечки памяти и проблемы потокобезопасности, переписать проблемные модули с правильными паттернами

**Target features:**
- Исправить HTTP session leaks (ProtocolExecutor, lifecycle.py, mailbox sessions)
- Исправить browser leaks (TempMailWebMailbox, PlaywrightExecutor)
- Исправить _task_locks memory leak (периодическая очистка)
- Исправить global state без locks (_HERO_SMS_CACHE, _FERNET, registries)
- Исправить scheduler/task shutdown (join threads)
- Исправить connection churn в SMS providers (persistent sessions)
- Исправить minor issues (lock ordering, subprocess pipes)

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
- ✓ Удалить Electron десктоп — v1.2
- ✓ Enterprise Email Provider Abstractions — v1.3

### Active

- [ ] Исправить HTTP session leaks
- [ ] Исправить browser leaks
- [ ] Исправить _task_locks memory leak
- [ ] Исправить global state без locks
- [ ] Исправить scheduler/task shutdown
- [ ] Исправить connection churn в SMS providers
- [ ] Исправить minor issues

### Out of Scope

- Рефакторинг монолитных файлов (кроме затронутых в этом milestone) — отдельный milestone
- Добавление тестов — отдельный milestone
- Масштабирование (PostgreSQL, connection pooling) — отдельный milestone
- Новые платформы — отдельный milestone

## Context

Brownfield проект. Выполнены v1.0 (Security), v1.1 (Tech Debt), v1.2 (Electron removal), v1.3 (Enterprise Email Provider Abstractions). Аудит выявил 29 проблем с утечками памяти и потокобезопасностью: HTTP session leaks, browser leaks, global state без locks, scheduler threads не join'ятся.

## Constraints

- **Tech Stack**: Python 3.12, FastAPI, SQLite, SQLAlchemy
- **Customer Portal**: Остаётся как отдельное приложение

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Удалить Electron + React | Дублирует веб, API покрывает всё | ✓ Good |
| Оставить core/desktop_apps.py | Детекция локальных IDE — core feature | ✓ Good |
| Оставить Customer Portal | Отдельное приложение, не связано с Electron | ✓ Good |
| Email subsystem clean break | Полный рефакторинг без обратной совместимости | ✓ Good |
| Single registry | Единый реестр вместо двух параллельных систем | ✓ Good |
| Full refactor for memory/thread | Переписать проблемные модули с правильными паттернами | — Pending |
| Clean break API | Меняем публичный API если нужно, без шимов | — Pending |

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
*Last updated: 2026-06-26 after v1.4 milestone start*
