# Any Auto Register

## What This Is

Мультиплатформенный инструмент для автоматической регистрации аккаунтов на 14+ сервисах (ChatGPT, Cursor, Windsurf, Trae, Kiro, Grok и др.). Python/FastAPI бэкенд. Использует browser automation (Playwright, Patchright, Camoufox) с anti-detection для обхода защит.

## Core Value

Автоматическая регистрация аккаунтов должна работать надёжно и безопасно — аккаунты создаются, данные защищены, система не подвержена компрометации.

## Current Milestone: v1.6 Scaling & Performance

**Goal:** Подготовить систему к production нагрузке — PostgreSQL, connection pooling, параллельная регистрация, rate limiting

**Target features:**
- PostgreSQL вместо SQLite
- Connection pooling для БД и HTTP
- Параллельная регистрация на多个 платформах
- Rate limiting для провайдеров

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
- ✓ Enterprise Cleanup — v1.5

### Active

- [ ] PostgreSQL вместо SQLite
- [ ] Connection pooling для БД
- [ ] Connection pooling для HTTP
- [ ] Параллельная регистрация
- [ ] Rate limiting для провайдеров

### Out of Scope

- Рефакторинг монолитных файлов (кроме затронутых в этом milestone) — отдельный milestone
- Добавление тестов — отдельный milestone
- Масштабирование (PostgreSQL, connection pooling) — отдельный milestone
- Новые платформы — отдельный milestone

## Context

Brownfield проект. Выполнены v1.0 (Security), v1.1 (Tech Debt), v1.2 (Electron removal), v1.3 (Enterprise Email Provider Abstractions), v1.4 (Memory Leaks & Thread Safety), v1.5 (Enterprise Cleanup). Кодовая база стабильна, приведена к enterprise-стандарту. SQLite работает для development, но нужна production-ready БД с connection pooling.

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
| Enterprise cleanup | Разделить монолиты, выделить паттерны, добавить типизацию | ✓ Good |
| PostgreSQL + pooling | Production-ready БД с connection pooling | — Pending |

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
*Last updated: 2026-06-27 after v1.6 milestone start*
