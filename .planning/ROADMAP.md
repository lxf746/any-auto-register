# Roadmap: v1.7 Frontend Rewrite + API Modernization

**Created:** 2026-06-27
**Phases:** 6
**Requirements:** 25 mapped

## Phase 1: Foundation + API v2

**Goal:** Настроить Next.js проект и обновить backend API

**Requirements:**
- FE-01: Next.js 14+ project setup with TypeScript, Tailwind CSS, Shadcn/ui
- API-01: API versioning — /api/v2/ prefix for new endpoints
- API-02: Response envelope —统一 {ok, data, error} format
- API-03: OpenAPI spec — auto-generated from FastAPI routes
- API-04: TypeScript gen — openapi-typescript for type-safe API calls

**Success Criteria:**
1. Next.js проект запускается и подключается к API
2. /api/v2/ endpoints работают с统一 форматом ответов
3. TypeScript types сгенерированы из OpenAPI
4. Authentication flow работает (login/register)

**Plans:** 2 plans

---

## Phase 2: Core UI

**Goal:** Основные страницы фронтенда

**Requirements:**
- FE-02: Authentication — JWT login/register pages with form validation
- FE-03: Dashboard — main overview page with platform cards and quick actions
- FE-04: Task Management — create, view, cancel registration tasks
- FE-05: Account List — view all registered accounts with search/filter

**Success Criteria:**
1. Login/Register страницы с валидацией форм
2. Dashboard показывает платформы и быстрые действия
3. Можно создать задачу регистрации из UI
4. Список аккаунтов с поиском и фильтрами

**Plans:** 2 plans

---

## Phase 3: Analytics Dashboard

**Goal:** Статистика и метрики

**Requirements:**
- AN-01: Registration stats — success/failure rates, timeline charts
- AN-02: Platform breakdown — per-platform registration metrics
- AN-03: Performance metrics — avg registration time, error rates
- AN-04: Export — download stats as CSV/JSON

**Success Criteria:**
1. Графики успеха/ошибок регистрации
2. Разбивка по платформам
3. Метрики производительности
4. Экспорт данных

**Plans:** 2 plans

---

## Phase 4: Real-time Updates

**Goal:** WebSocket для реалтайм обновлений

**Requirements:**
- RT-01: WebSocket connection — establish WS for live task updates
- RT-02: Task status streaming — real-time progress without polling
- RT-03: Connection management — reconnect on disconnect, heartbeat
- API-05: WebSocket endpoint — /api/v2/ws for real-time updates

**Success Criteria:**
1. WebSocket подключение работает
2. Статус задач обновляется в реальном времени
3. Автоматическое переподключение при разрыве

**Plans:** 2 plans

---

## Phase 5: Settings Management

**itude:** Управление настройками через UI

**Requirements:**
- SM-01: Mailbox providers — enable/disable/configure providers
- SM-02: SMS providers — manage SMS verification providers
- SM-03: Captcha providers — configure captcha solving services
- SM-04: Proxy settings — manage proxy list and rotation
- SM-05: Platform config — per-platform rate limits and settings

**Success Criteria:**
1. UI для управления всеми типами провайдеров
2. Настройки прокси с добавлением/удалением
3. Конфигурация платформ (rate limits, executor types)

**Plans:** 2 plans

---

## Phase 6: Logs & Debug

**Goal:** Просмотр логов и отладка

**Requirements:**
- LD-01: Task logs — view detailed logs per registration task
- LD-02: Error viewer — filter and search errors with stack traces
- LD-03: Debug mode — step-by-step registration flow visualization

**Success Criteria:**
1. Логи доступны для каждой задачи
2. Ошибки фильтруются и ищутся
3. Debug mode показывает пошаговый flow регистрации

**Plans:** 2 plans

---

## Progress

| Phase | Goal | Requirements | Status | Completed |
|-------|------|--------------|--------|-----------|
| 1. Foundation + API v2 | Next.js setup, API v2 | FE-01, API-01–04 | Not started | — |
| 2. Core UI | Dashboard, tasks, accounts | FE-02–05 | Not started | — |
| 3. Analytics Dashboard | Stats, charts, metrics | AN-01–04 | Not started | — |
| 4. Real-time Updates | WebSocket | RT-01–03, API-05 | Not started | — |
| 5. Settings Management | Provider config UI | SM-01–05 | Not started | — |
| 6. Logs & Debug | Logging, debug | LD-01–03 | Not started | — |
