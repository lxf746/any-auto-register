# Any Auto Register

## What This Is

Мультиплатформенный инструмент для автоматической регистрации аккаунтов на 14+ сервисах (ChatGPT, Cursor, Windsurf, Trae, Kiro, Grok и др.). Python/FastAPI бэкенд. Использует browser automation (Playwright, Patchright, Camoufox) с anti-detection для обхода защит.

## Core Value

Автоматическая регистрация аккаунтов должна работать надёжно и безопасно — аккаунты создаются, данные защищены, система не подвержена компрометации.

## Current Milestone: v1.7 Frontend Rewrite + API Modernization

**Goal:** Полный rewrite фронтенда на Next.js + обновление backend API

**Target features:**
- Next.js 14+ с TypeScript, Tailwind CSS, Shadcn/ui
- Analytics Dashboard — статистика, графики, метрики регистраций
- Real-time Updates — WebSocket вместо polling для статуса задач
- Settings Management — UI для управления прокси, провайдерами, настройками
- Logs & Debug — просмотр логов, ошибок, отладка registration flow
- Backend API v2 — versioning, response envelope, OpenAPI → TypeScript gen

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
- ✓ PostgreSQL вместо SQLite — v1.6
- ✓ Connection pooling для БД и HTTP — v1.6
- ✓ Параллельная регистрация — v1.6
- ✓ Rate limiting для провайдеров — v1.6

### Active

- [ ] Next.js frontend с TypeScript, Tailwind, Shadcn
- [ ] Analytics Dashboard
- [ ] Real-time Updates (WebSocket)
- [ ] Settings Management UI
- [ ] Logs & Debug界面
- [ ] Backend API v2 (versioning, envelope, OpenAPI gen)

### Out of Scope

- Рефакторинг монолитных файлов — отдельный milestone
- Добавление тестов — отдельный milestone
- Новые платформы — отдельный milestone
- Горизонтальное масштабирование — отдельный milestone
- Mobile app — web-first

## Context

Brownfield проект. Выполнены v1.0 (Security), v1.1 (Tech Debt), v1.2 (Electron removal), v1.3 (Enterprise Email Provider Abstractions), v1.4 (Memory Leaks & Thread Safety), v1.5 (Enterprise Cleanup), v1.6 (Scaling & Performance). 73 файла изменено, +7803/-725 строк. PostgreSQL с connection pooling, параллельная регистрация, rate limiting — всё готово для production нагрузки.

## Constraints

- **Tech Stack**: Python 3.12, FastAPI, PostgreSQL (SQLite for dev), SQLAlchemy
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
| PostgreSQL + pooling | Production-ready БД с connection pooling | ✓ Good |
| Sync-first PostgreSQL | asyncpg→psycopg2 normalization, 94 Session call sites unchanged | ✓ Good |
| BrowserPool factory | create_browser_pool() + интеграция в 3 платформы | ✓ Good |
| Rate limit preflight | check_platform_limit() в entry point каждой flow | ✓ Good |
| retry_with_backoff | Exponential backoff + jitter в HTTPClient | ✓ Good |

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
*Last updated: 2026-06-27 after v1.7 milestone start*
