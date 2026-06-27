# Any Auto Register

## What This Is

Мультиплатформенный инструмент для автоматической регистрации аккаунтов на 14+ сервисах (ChatGPT, Cursor, Windsurf, Trae, Kiro, Grok и др.). Python/FastAPI бэкенд. Использует browser automation (Playwright, Patchright, Camoufox) с anti-detection для обхода защит.

## Core Value

Автоматическая регистрация аккаунтов должна работать надёжно и безопасно — аккаунты создаются, данные защищены, система не подвержена компрометации.

## Current Milestone: v1.5 Enterprise Cleanup

**Goal:** Привести кодовую базу к enterprise-стандарту — разделить монолиты, выделить общие паттерны, убрать дублирование, добавить типизацию

**Target features:**
- Разделить монолитные файлы (base_sms.py, chatgpt/browser_register.py, db.py)
- Выделить общие паттерны (ManagedSession, BasePollingMailbox, retry)
- Объединить дублирующие директории (core/mailbox/ vs providers/mailbox/)
- Добавить type hints и заменить Any на конкретные типы

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
- ✓ Memory Leaks & Thread Safety — v1.4

### Active

- [ ] Разделить base_sms.py на модули
- [ ] Разделить chatgpt/browser_register.py на модули
- [ ] Разделить db.py на models/engine/migrations
- [ ] Extract ManagedSession mixin
- [ ] Extract BasePollingMailbox
- [ ] Extract retry utility
- [ ] Consolidate core/mailbox/ vs providers/mailbox/
- [ ] Type hints для BasePlatform
- [ ] Replace Any на конкретные типы

### Out of Scope

- Рефакторинг монолитных файлов (кроме затронутых в этом milestone) — отдельный milestone
- Добавление тестов — отдельный milestone
- Масштабирование (PostgreSQL, connection pooling) — отдельный milestone
- Новые платформы — отдельный milestone

## Context

Brownfield проект. Выполнены v1.0 (Security), v1.1 (Tech Debt), v1.2 (Electron removal), v1.3 (Enterprise Email Provider Abstractions), v1.4 (Memory Leaks & Thread Safety). Кодовая база стабильна, готова к масштабному рефакторингу. Выявлено 6 монолитных файлов (1000+ строк), дублирование паттернов в 8+ файлах, отсутствие типизации в ключевых модулях.

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
| Full refactor for memory/thread | Переписать проблемные модули с правильными паттернами | ✓ Good |
| Clean break API | Меняем публичный API если нужно, без шимов | ✓ Good |
| Enterprise cleanup | Разделить монолиты, выделить паттерны, добавить типизацию | — Pending |

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
*Last updated: 2026-06-27 after v1.5 milestone start*
